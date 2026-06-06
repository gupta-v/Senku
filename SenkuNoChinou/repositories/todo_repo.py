from datetime import datetime

from beanie import PydanticObjectId

from SenkuNoChinou.models.dataSchema import Todo


def _to_dict(doc: Todo) -> dict:
    d = doc.model_dump()
    d["_id"] = str(doc.id)
    return d


async def insert_todo(
    task: str,
    priority: str,
    due_date: str,
    due_time: str = "",
    note: str = "",
    status: str = "pending",
) -> str:
    todo = Todo(
        task=task,
        priority=priority,
        due_date=due_date,
        due_time=due_time,
        note=note,
        status=status,
        completed_at=datetime.utcnow() if status == "done" else None,
    )
    await todo.insert()
    return str(todo.id)


async def get_todos(status: str = "pending", due_date: str = "") -> list[dict]:
    conditions = []
    if status:
        conditions.append(Todo.status == status)
    if due_date:
        conditions.append(Todo.due_date == due_date)
    docs = await Todo.find(*conditions).sort("-created_at").to_list()
    return [_to_dict(d) for d in docs]


async def update_todo(todo_id: str, **fields) -> bool:
    todo = await Todo.get(PydanticObjectId(todo_id))
    if not todo:
        return False
    fields["updated_at"] = datetime.utcnow()
    await todo.update({"$set": fields})
    return True


async def mark_done(todo_id: str) -> bool:
    return await update_todo(todo_id, status="done", completed_at=datetime.utcnow())
