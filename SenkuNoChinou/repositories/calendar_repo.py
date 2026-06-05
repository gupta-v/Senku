from datetime import datetime, timedelta

from bson import ObjectId

from SenkuNoChinou.repositories.database import events


async def insert_event(
    title: str,
    event_datetime: datetime,
    notes: str = "",
) -> str:
    """Insert a calendar event and return its string ID."""
    doc = {
        "title": title,
        "event_datetime": event_datetime,
        "notes": notes,
        "created_at": datetime.utcnow(),
        "reminder_sent": False,
    }
    result = await events().insert_one(doc)
    return str(result.inserted_id)


async def get_events(upcoming_only: bool = True, limit: int = 20) -> list[dict]:
    """Return calendar events, optionally only future ones."""
    query: dict = {}
    if upcoming_only:
        query["event_datetime"] = {"$gte": datetime.utcnow()}
    cursor = events().find(query).sort("event_datetime", 1)
    docs = await cursor.to_list(length=limit)
    for d in docs:
        d["_id"] = str(d["_id"])
    return docs


async def get_events_needing_reminder(window_minutes: int = 2) -> list[dict]:
    """
    Return events whose datetime falls within the next [15, 15+window_minutes]
    minutes that have not yet had their reminder sent.
    Called by the scheduler every 60 s.
    """
    now = datetime.utcnow()
    lo = now + timedelta(minutes=14)
    hi = now + timedelta(minutes=15 + window_minutes)
    query = {
        "event_datetime": {"$gte": lo, "$lte": hi},
        "reminder_sent": False,
    }
    cursor = events().find(query)
    docs = await cursor.to_list(length=50)
    for d in docs:
        d["_id"] = str(d["_id"])
    return docs


async def mark_reminder_sent(event_id: str) -> None:
    await events().update_one(
        {"_id": ObjectId(event_id)},
        {"$set": {"reminder_sent": True}},
    )


async def update_event(event_id: str, **fields) -> bool:
    """Patch arbitrary fields on an event. Returns True if modified."""
    fields["updated_at"] = datetime.utcnow()
    result = await events().update_one(
        {"_id": ObjectId(event_id)},
        {"$set": fields},
    )
    return result.modified_count > 0


async def delete_event(event_id: str) -> bool:
    result = await events().delete_one({"_id": ObjectId(event_id)})
    return result.deleted_count > 0
