import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

# Render mounts secret file at /etc/secrets/.env — load before anything else
_secrets = Path("/etc/secrets/.env")
load_dotenv(_secrets if _secrets.exists() else Path(".env"))

import uvicorn
from fastapi import FastAPI

from SenkuNoChinou.controllers.api import router as senku_router
from SenkuNoChinou.core.workflow import build_workflow
from SenkuNoChinou.services.stt import STTService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.stt = STTService()
    app.state.workflow = None  # None until background init completes

    async def _init_workflow():
        async with build_workflow() as wf:
            app.state.workflow = wf
            log.info("workflow ready — accepting requests")
            await asyncio.get_event_loop().create_future()  # hold context open

    task = asyncio.create_task(_init_workflow())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass


app = FastAPI(title="SenkuNoChinou", lifespan=lifespan)
app.include_router(senku_router)


