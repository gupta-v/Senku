import logging
import os

import certifi
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient

from SenkuNoChinou.models.dataSchema import Todo, Event, JournalEntry

log = logging.getLogger("senku.db")

_client: AsyncIOMotorClient | None = None


def _get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        uri = os.environ["MONGODB_URI"]
        _client = AsyncIOMotorClient(uri, tlsCAFile=certifi.where())
        log.info("MongoDB Motor client initialised")
    return _client


async def ping() -> bool:
    """Verify connection and initialise Beanie. Called at startup."""
    try:
        client = _get_client()
        await client.admin.command("ping")
        await init_beanie(
            database=client["senku"],
            document_models=[Todo, Event, JournalEntry],
        )
        log.info("MongoDB ping OK + Beanie initialised")
        return True
    except Exception as exc:
        log.error("MongoDB ping failed: %s", exc)
        return False


async def close() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None
        log.info("MongoDB client closed")
