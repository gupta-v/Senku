"""
Todo tools — add, list, complete, edit.

Raw async functions are registered by todo_server.py (fastmcp).
LangChain wrappers at the bottom are used directly by workflow.py.
"""
import logging
import re
from datetime import date

from langchain.tools import tool

from SenkuNoChinou.repositories import todo_repo

log = logging.getLogger("senku.tools.todo")

_PRIORITY_EMOJI = {"low": "🟢", "medium": "🟡", "high": "🔴", "urgent": "🚨"}


async def add_todo(task: str = "", title: str = "", priority: str = "medium", due_date: str = "", due_time: str = "", note: str = "", status: str = "pending") -> str:
    """
    Add a new task to the todo list.

    Args:
        task: Clear, concise title for the task (rephrase if needed, preserve intent). Also accepts 'title' as alias.
        priority: low | medium | high | urgent. Default medium.
        due_date: Target date in YYYY-MM-DD format. MUST be resolved via get_datetime first — never guess the year.
        due_time: Expected finish time in HH:MM format (optional).
        note: Extra context — URLs, details, reminders (optional).
        status: pending | done. Use 'done' if user says the task is already completed. Default pending.
            NOTE: past due dates are ONLY allowed when status='done'. Pending todos must have today or a future date.

    Returns:
        Confirmation string with the todo ID.
    """
    task = task or title
    if not task:
        return "⚠️ No task provided. Pass the task name."
    priority = priority.lower() if priority.lower() in _PRIORITY_EMOJI else "medium"
    status = status.lower() if status.lower() in ("pending", "done") else "pending"

    if due_date and status != "done":
        try:
            parsed = date.fromisoformat(due_date)
            if parsed < date.today():
                return (
                    f"⚠️ Cannot add pending todo with a past due date ({due_date}). "
                    "Use status='done' for completed tasks, or set a current/future due date."
                )
        except ValueError:
            return f"⚠️ Invalid due_date format '{due_date}'. Use YYYY-MM-DD."

    todo_id = await todo_repo.insert_todo(task, priority, due_date, due_time, note, status)
    emoji = _PRIORITY_EMOJI[priority]
    due = f" · due {due_date}" + (f" {due_time}" if due_time else "") if due_date else ""
    status_label = " ✓" if status == "done" else ""
    msg = f"{emoji} Added{status_label}: {task}{due}"
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
        lines.append(f"  {emoji} [id:{d['_id']}] {d['task']}{due_str}{note_str} [{d.get('priority','medium')}]")
    return "\n".join(lines)


_OID_RE = re.compile(r'^[0-9a-fA-F]{24}$')


async def _resolve_todo_id(todo_id_or_name: str) -> tuple[str, str] | str:
    """Return (id, task_name) or an error string."""
    if _OID_RE.match(todo_id_or_name):
        return todo_id_or_name, todo_id_or_name[:8]
    needle = todo_id_or_name.lower().strip()
    needle_norm = needle.replace(" ", "")

    def _match(task: str) -> bool:
        t = task.lower()
        return needle in t or (needle_norm and needle_norm in t.replace(" ", ""))

    pending = await todo_repo.get_todos(status="pending")
    matches = [d for d in pending if _match(d["task"])]
    if not matches:
        done = await todo_repo.get_todos(status="done")
        done_matches = [d for d in done if _match(d["task"])]
        if done_matches:
            return f"ℹ️ '{done_matches[0]['task']}' is already marked as done."
        names = ", ".join(f"'{d['task']}'" for d in pending[:5])
        return f"❌ No pending todo matches '{todo_id_or_name}'. Pending: {names or 'none'}."
    if len(matches) > 1:
        names = ", ".join(f"'{d['task']}'" for d in matches)
        return f"❌ Multiple todos match '{todo_id_or_name}': {names}. Be more specific."
    return matches[0]["_id"], matches[0]["task"]


async def complete_todo(todo_id: str) -> str:
    """
    Mark a todo as done.

    Args:
        todo_id: The full 24-char ID from list_todos, OR a keyword/partial name of the task.

    Returns:
        Confirmation string.
    """
    resolved = await _resolve_todo_id(todo_id)
    if isinstance(resolved, str):
        return resolved
    real_id, label = resolved
    ok = await todo_repo.mark_done(real_id)
    if not ok:
        return f"❌ Todo '{label}' not found or already done."
    return f"✅ '{label}' marked as done."


async def edit_todo(todo_id: str, task: str = "", priority: str = "", due_date: str = "", due_time: str = "", note: str = "") -> str:
    """
    Edit an existing todo's fields. Only pass the fields you want to change.

    Args:
        todo_id: The full 24-char ID from list_todos, OR a keyword/partial name of the task.
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

    if due_date:
        try:
            if date.fromisoformat(due_date) < date.today():
                return (
                    f"⚠️ Cannot set a past due date ({due_date}) on a todo. "
                    "Use today or a future date."
                )
        except ValueError:
            return f"⚠️ Invalid due_date format '{due_date}'. Use YYYY-MM-DD."

    resolved = await _resolve_todo_id(todo_id)
    if isinstance(resolved, str):
        return resolved
    real_id, label = resolved

    ok = await todo_repo.update_todo(real_id, **updates)
    if not ok:
        return f"❌ Todo '{label}' not found."
    changed = ", ".join(f"{k}={v}" for k, v in updates.items())
    return f"✅ '{label}' updated: {changed}"


# ── LangChain tool wrappers (used by workflow.py direct_tools) ────────────────
add_todo_lc      = tool(add_todo)
list_todos_lc    = tool(list_todos)
complete_todo_lc = tool(complete_todo)
edit_todo_lc     = tool(edit_todo)
