from datetime import datetime

from bson import ObjectId

from SenkuNoChinou.repositories.database import todos


async def insert_todo(
    task: str,
    priority: str,
    due_date: str,
    due_time: str = "",
    note: str = "",
    status: str = "pending",
) -> str:
    """Insert a new todo and return its string ID."""
    doc = {
        "task": task,
        "priority": priority,
        "due_date": due_date,
        "due_time": due_time,
        "note": note,
        "status": status,
        "created_at": datetime.utcnow(),
        "completed_at": datetime.utcnow() if status == "done" else None,
    }
    result = await todos().insert_one(doc)
    return str(result.inserted_id)


async def get_todos(status: str = "pending", due_date: str = "") -> list[dict]:
    """Return todos filtered by status and optionally by date."""
    query: dict = {}
    if status:
        query["status"] = status
    if due_date:
        query["due_date"] = due_date
    cursor = todos().find(query).sort("created_at", -1)
    docs = await cursor.to_list(length=200)
    for d in docs:
        d["_id"] = str(d["_id"])
    return docs


async def update_todo(todo_id: str, **fields) -> bool:
    """Patch arbitrary fields on a todo. Returns True if modified."""
    fields["updated_at"] = datetime.utcnow()
    result = await todos().update_one(
        {"_id": ObjectId(todo_id)},
        {"$set": fields},
    )
    return result.modified_count > 0


async def mark_done(todo_id: str) -> bool:
    """Mark a todo as done."""
    return await update_todo(
        todo_id,
        status="done",
        completed_at=datetime.utcnow(),
    )
