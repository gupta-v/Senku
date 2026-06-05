"""
Todo tools — add, list, complete, edit.
Auto-sends ntfy on every write operation.

Raw async functions are registered by todo_server.py (fastmcp).
LangChain wrappers at the bottom are used directly by workflow.py.
"""
import asyncio
import logging

from langchain.tools import tool

from SenkuNoChinou.MCP.tools.ntfy_tool import send_notification
from SenkuNoChinou.repositories import todo_repo

log = logging.getLogger("senku.tools.todo")

_PRIORITY_EMOJI = {"low": "🟢", "medium": "🟡", "high": "🔴", "urgent": "🚨"}


async def _notify(message: str, title: str = "Senku · Todo", priority: int = 3, tags: list[str] | None = None) -> None:
    await asyncio.to_thread(send_notification, message, title, priority, tags or [])


async def add_todo(task: str, priority: str = "medium", due_date: str = "", due_time: str = "", note: str = "", status: str = "pending") -> str:
    """
    Add a new task to the todo list.

    Args:
        task: Clear, concise title for the task (rephrase if needed, preserve intent).
        priority: low | medium | high | urgent. Default medium.
        due_date: Target date in YYYY-MM-DD format. MUST be resolved via get_datetime first — never guess the year.
        due_time: Expected finish time in HH:MM format (optional).
        note: Extra context — URLs, details, reminders (optional).
        status: pending | done. Use 'done' if user says the task is already completed. Default pending.

    Returns:
        Confirmation string with the todo ID.
    """
    priority = priority.lower() if priority.lower() in _PRIORITY_EMOJI else "medium"
    status = status.lower() if status.lower() in ("pending", "done") else "pending"
    todo_id = await todo_repo.insert_todo(task, priority, due_date, due_time, note, status)
    emoji = _PRIORITY_EMOJI[priority]
    due = f" · due {due_date}" + (f" {due_time}" if due_time else "") if due_date else ""
    status_label = " ✓" if status == "done" else ""
    msg = f"{emoji} Added{status_label}: {task}{due}"
    await _notify(msg, tags=["pencil"])
    log.info("add_todo id=%s task=%r status=%s", todo_id, task, status)
    return f"✅ Todo added (ID: {todo_id})\n{msg}"


async def list_todos(status: str = "pending", due_date: str = "") -> str:
    """
    List todos from the database.

    Args:
        status: Filter by status — pending | done | (empty for all). Default pending.
        due_date: Filter by date YYYY-MM-DD (optional, leave empty for all dates).

    Returns:
        Formatted list of todos.
    """
    docs = await todo_repo.get_todos(status=status, due_date=due_date)
    if not docs:
        label = f"No {status} todos" + (f" for {due_date}" if due_date else "")
        return f"📋 {label}."
    lines = [f"📋 {status.capitalize()} todos ({len(docs)}):"]
    for d in docs:
        emoji = _PRIORITY_EMOJI.get(d.get("priority", "medium"), "🟡")
        due = d.get("due_date", "")
        time_ = d.get("due_time", "")
        due_str = f" · {due}" + (f" {time_}" if time_ else "") if due else ""
        note_str = f" · {d['note']}" if d.get("note") else ""
        lines.append(f"  {emoji} [{d['_id'][:8]}] {d['task']}{due_str}{note_str} [{d.get('priority','medium')}]")
    return "\n".join(lines)


async def complete_todo(todo_id: str) -> str:
    """
    Mark a todo as done.

    Args:
        todo_id: The full ID returned when the todo was added.

    Returns:
        Confirmation string.
    """
    ok = await todo_repo.mark_done(todo_id)
    if not ok:
        return f"❌ Todo {todo_id[:8]} not found or already done."
    await _notify(f"✅ Done: todo {todo_id[:8]}", tags=["white_check_mark"])
    return f"✅ Todo {todo_id[:8]} marked as done."


async def edit_todo(todo_id: str, task: str = "", priority: str = "", due_date: str = "", due_time: str = "", note: str = "") -> str:
    """
    Edit an existing todo's fields. Only pass the fields you want to change.

    Args:
        todo_id: The full ID returned when the todo was added.
        task: New task title (optional).
        priority: New priority — low | medium | high | urgent (optional).
        due_date: New due date YYYY-MM-DD (optional).
        due_time: New due time HH:MM (optional).
        note: New note / URL / extra context (optional).

    Returns:
        Confirmation string.
    """
    updates = {k: v for k, v in {"task": task, "priority": priority, "due_date": due_date, "due_time": due_time, "note": note}.items() if v}
    if not updates:
        return "⚠️ No fields provided to update."
    ok = await todo_repo.update_todo(todo_id, **updates)
    if not ok:
        return f"❌ Todo {todo_id[:8]} not found."
    changed = ", ".join(f"{k}={v}" for k, v in updates.items())
    await _notify(f"✏️ Updated todo {todo_id[:8]}: {changed}", tags=["pencil2"])
    return f"✅ Todo {todo_id[:8]} updated: {changed}"


# ── LangChain tool wrappers (used by workflow.py direct_tools) ────────────────
add_todo_lc      = tool(add_todo)
list_todos_lc    = tool(list_todos)
complete_todo_lc = tool(complete_todo)
edit_todo_lc     = tool(edit_todo)
