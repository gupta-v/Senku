import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

# Render mounts secret file at /etc/secrets/.env — load before anything else
_secrets = Path("/etc/secrets/.env")
load_dotenv(_secrets if _secrets.exists() else Path(".env"))

import uvicorn
from fastapi import FastAPI

from SenkuNoChinou.controllers.api import router as senku_router
from SenkuNoChinou.controllers.gif_router import gif_router
from SenkuNoChinou.core.workflow import build_workflow
from SenkuNoChinou.core.scheduler import run_scheduler
from SenkuNoChinou.core.server import run_mcp_servers, ICHI_PORT, NI_PORT, SAN_PORT, GO_PORT
from SenkuNoChinou.repositories.database import ping as db_ping, close as db_close
from SenkuNoChinou.services.stt import STTService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)

log = logging.getLogger("senku.main")

_MCP_READY_TIMEOUT = float(os.getenv("MCP_READY_TIMEOUT", "10.0"))


async def _await_mcp_ports(ports: list[int], timeout: float = _MCP_READY_TIMEOUT) -> None:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    for port in ports:
        while loop.time() < deadline:
            try:
                _, writer = await asyncio.wait_for(
                    asyncio.open_connection("127.0.0.1", port), timeout=0.3
                )
                writer.close()
                await writer.wait_closed()
                log.debug("MCP port %d ready", port)
                break
            except Exception:
                await asyncio.sleep(0.2)
        else:
            log.warning("MCP port %d not ready within %.1fs", port, timeout)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── DB ping ──────────────────────────────────────────────────────────────
    await db_ping()

    app.state.stt = STTService()
    app.state.workflow = None

    # ── MCP servers (in-process when MCP_HOST is localhost) ──────────────────
    mcp_host = os.getenv("MCP_HOST", "localhost")
    mcp_task = None
    if mcp_host == "localhost":
        log.info("starting MCP servers in-process (MCP_HOST=localhost)")
        mcp_task = asyncio.create_task(run_mcp_servers())
        await _await_mcp_ports([ICHI_PORT, NI_PORT, SAN_PORT, GO_PORT])

    # ── Workflow init (background) ───────────────────────────────────────────
    async def _init_workflow():
        async with build_workflow() as wf:
            app.state.workflow = wf
            log.info("workflow ready — accepting requests")
            await asyncio.get_running_loop().create_future()

    workflow_task = asyncio.create_task(_init_workflow())

    # ── Calendar scheduler (background) ──────────────────────────────────────
    scheduler_task = asyncio.create_task(run_scheduler())

    try:
        yield
    finally:
        for task in (t for t in (mcp_task, workflow_task, scheduler_task) if t):
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
        await db_close()


app = FastAPI(title="SenkuNoChinou", lifespan=lifespan)
app.include_router(senku_router)
app.include_router(gif_router)


