"""
Runs all four MCP servers as in-process HTTP endpoints.

Instead of spawning `uv run fastmcp run ...` subprocesses (which each fork a
full Python interpreter), all servers share the same runtime as the FastAPI app.

Usage — call from main.py lifespan:
    mcp_task = asyncio.create_task(run_mcp_servers())
"""
import asyncio
import logging
import os
import sys

# Allow running standalone: python SenkuNoChinou/core/server.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from dotenv import load_dotenv
load_dotenv()

from SenkuNoChinou.MCP.servers.ichi_server import mcp as ichi_mcp
from SenkuNoChinou.MCP.servers.ni_server import mcp as ni_mcp
from SenkuNoChinou.MCP.servers.san_server import mcp as san_mcp
from SenkuNoChinou.MCP.servers.go_server import mcp as go_mcp

log = logging.getLogger("senku.mcpserver")

# ── Port / host config (override via env) ─────────────────────────────────────
MCP_HOST  = os.getenv("MCP_HOST", "localhost")
ICHI_PORT = int(os.getenv("ICHI_SERVER_PORT", "8081"))
NI_PORT   = int(os.getenv("NI_SERVER_PORT",   "8082"))
SAN_PORT  = int(os.getenv("SAN_SERVER_PORT",  "8083"))
GO_PORT   = int(os.getenv("GO_SERVER_PORT",   "8084"))

# ── URLs for the MCP client in gear definitions ───────────────────────────────
ICHI_URL = f"http://{MCP_HOST}:{ICHI_PORT}/mcp"
NI_URL   = f"http://{MCP_HOST}:{NI_PORT}/mcp"
SAN_URL  = f"http://{MCP_HOST}:{SAN_PORT}/mcp"
GO_URL   = f"http://{MCP_HOST}:{GO_PORT}/mcp"

# Seconds to wait after servers start before workflow connects to them
_STARTUP_GRACE = float(os.getenv("MCP_STARTUP_GRACE", "2.0"))


async def run_mcp_servers() -> None:
    """
    Start all MCP HTTP servers concurrently.
    Meant to run as a background asyncio task from lifespan.
    """
    from SenkuNoChinou.repositories.database import ping as db_ping
    await db_ping()

    log.info(
        "MCP servers starting — ichi:%d  ni:%d  san:%d  go:%d",
        ICHI_PORT, NI_PORT, SAN_PORT, GO_PORT,
    )
    log.info("  ichi → %s", ICHI_URL)
    log.info("  ni   → %s", NI_URL)
    log.info("  san  → %s", SAN_URL)
    log.info("  go   → %s", GO_URL)

    await asyncio.gather(
        ichi_mcp.run_http_async(host="0.0.0.0", port=ICHI_PORT),
        ni_mcp.run_http_async(host="0.0.0.0", port=NI_PORT),
        san_mcp.run_http_async(host="0.0.0.0", port=SAN_PORT),
        go_mcp.run_http_async(host="0.0.0.0", port=GO_PORT),
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    print(f"  ichi → {ICHI_URL}")
    print(f"  ni   → {NI_URL}")
    print(f"  san  → {SAN_URL}")
    print(f"  go   → {GO_URL}")
    asyncio.run(run_mcp_servers())
