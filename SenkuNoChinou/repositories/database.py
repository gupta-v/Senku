import logging
import os

from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorCollection,
    AsyncIOMotorDatabase,
)

log = logging.getLogger("senku.db")

_client: AsyncIOMotorClient | None = None


def _get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        uri = os.environ["MONGODB_URI"]
        _client = AsyncIOMotorClient(uri)
        log.info("MongoDB Motor client initialised")
    return _client


def get_db() -> AsyncIOMotorDatabase:
    return _get_client()["senku"]


# ── Collection accessors ──────────────────────────────────────────────────────

def todos() -> AsyncIOMotorCollection:
    return get_db()["todos"]


def events() -> AsyncIOMotorCollection:
    return get_db()["events"]


def journal() -> AsyncIOMotorCollection:
    return get_db()["journal"]


async def ping() -> bool:
    """Verify the connection is alive. Called at startup."""
    try:
        await _get_client().admin.command("ping")
        log.info("MongoDB ping OK")
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
