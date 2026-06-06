from datetime import datetime, timezone

from bson import ObjectId

from SenkuNoChinou.repositories.database import journal


async def insert_entry(
    content: str,
    mood: str = "",
    tags: list[str] | None = None,
) -> str:
    """Insert a journal entry and return its string ID."""
    now = datetime.utcnow()
    doc = {
        "content": content,
        "mood": mood,
        "tags": tags or [],
        "created_at": now,
        "updated_at": now,
    }
    result = await journal().insert_one(doc)
    return str(result.inserted_id)


async def get_entries(days: int = 7, tag: str = "", limit: int = 50) -> list[dict]:
    """Return recent journal entries, optionally filtered by tag."""
    query: dict = {}
    if days:
        since = datetime.utcnow() - __import__("datetime").timedelta(days=days)
        query["created_at"] = {"$gte": since}
    if tag:
        query["tags"] = tag
    cursor = journal().find(query).sort("created_at", -1)
    docs = await cursor.to_list(length=limit)
    for d in docs:
        d["_id"] = str(d["_id"])
    return docs


async def update_entry(entry_id: str, content: str) -> bool:
    """Update journal entry content. Returns True if modified."""
    result = await journal().update_one(
        {"_id": ObjectId(entry_id)},
        {"$set": {"content": content, "updated_at": datetime.utcnow()}},
    )
    return result.modified_count > 0
