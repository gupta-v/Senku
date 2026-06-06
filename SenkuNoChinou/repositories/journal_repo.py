from datetime import datetime, timedelta

from beanie import PydanticObjectId

from SenkuNoChinou.models.dataSchema import JournalEntry


def _to_dict(doc: JournalEntry) -> dict:
    d = doc.model_dump()
    d["_id"] = str(doc.id)
    return d


async def insert_entry(content: str, mood: str = "", tags: list[str] | None = None) -> str:
    entry = JournalEntry(content=content, mood=mood, tags=tags or [])
    await entry.insert()
    return str(entry.id)


async def get_entries(days: int = 7, tag: str = "", limit: int = 50) -> list[dict]:
    query: dict = {}
    if days:
        since = datetime.utcnow() - timedelta(days=days)
        query["created_at"] = {"$gte": since}
    if tag:
        query["tags"] = tag
    docs = await JournalEntry.find(query).sort("-created_at").limit(limit).to_list()
    return [_to_dict(d) for d in docs]


async def update_entry(entry_id: str, content: str) -> bool:
    entry = await JournalEntry.get(PydanticObjectId(entry_id))
    if not entry:
        return False
    await entry.update({"$set": {"content": content, "updated_at": datetime.utcnow()}})
    return True
