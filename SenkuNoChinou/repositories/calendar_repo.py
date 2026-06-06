from datetime import datetime, timedelta

from beanie import PydanticObjectId

from SenkuNoChinou.models.dataSchema import Event


def _to_dict(doc: Event) -> dict:
    d = doc.model_dump()
    d["_id"] = str(doc.id)
    return d


async def insert_event(title: str, event_datetime: datetime, notes: str = "") -> str:
    event = Event(title=title, event_datetime=event_datetime, notes=notes)
    await event.insert()
    return str(event.id)


async def get_events(upcoming_only: bool = True, limit: int = 20) -> list[dict]:
    query: dict = {}
    if upcoming_only:
        query["event_datetime"] = {"$gte": datetime.utcnow()}
    docs = await Event.find(query).sort("+event_datetime").limit(limit).to_list()
    return [_to_dict(d) for d in docs]


async def get_events_needing_reminder(window_minutes: int = 2) -> list[dict]:
    now = datetime.utcnow()
    lo = now + timedelta(minutes=14)
    hi = now + timedelta(minutes=15 + window_minutes)
    docs = await Event.find({
        "event_datetime": {"$gte": lo, "$lte": hi},
        "reminder_sent": False,
    }).to_list()
    return [_to_dict(d) for d in docs]


async def mark_reminder_sent(event_id: str) -> None:
    event = await Event.get(PydanticObjectId(event_id))
    if event:
        await event.update({"$set": {"reminder_sent": True}})


async def update_event(event_id: str, **fields) -> bool:
    event = await Event.get(PydanticObjectId(event_id))
    if not event:
        return False
    fields["updated_at"] = datetime.utcnow()
    await event.update({"$set": fields})
    return True


async def delete_event(event_id: str) -> bool:
    event = await Event.get(PydanticObjectId(event_id))
    if not event:
        return False
    await event.delete()
    return True
