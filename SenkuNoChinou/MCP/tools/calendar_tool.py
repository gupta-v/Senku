"""
Calendar tools — add, list, delete events.
Auto-sends ntfy on add. Scheduler handles 15-min reminders separately.

Raw async functions registered by calendar_server.py (fastmcp).
LangChain wrappers at the bottom used directly by workflow.py.
"""
import asyncio
import logging
from datetime import datetime

from langchain.tools import tool

from SenkuNoChinou.MCP.tools.ntfy_tool import send_notification
from SenkuNoChinou.repositories import calendar_repo

log = logging.getLogger("senku.tools.calendar")


async def _notify(message: str, title: str = "Senku · Calendar", priority: int = 3, tags: list[str] | None = None) -> None:
    await asyncio.to_thread(send_notification, message, title, priority, tags or [])


def _parse_dt(dt_str: str) -> datetime:
    """Try common ISO-like formats."""
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse datetime: {dt_str!r}. Use YYYY-MM-DD HH:MM")


async def add_event(title: str, event_datetime: str, notes: str = "") -> str:
    """
    Add an event to the calendar.

    Args:
        title: Event name or description (e.g. 'Meeting with infra').
        event_datetime: Date and time in YYYY-MM-DD HH:MM format (e.g. '2026-06-06 18:45').
        notes: Optional extra details about the event.

    Returns:
        Confirmation with event ID. A reminder ntfy will fire 15 minutes before.
    """
    try:
        dt = _parse_dt(event_datetime)
    except ValueError as e:
        return f"❌ {e}"
    event_id = await calendar_repo.insert_event(title, dt, notes)
    dt_str = dt.strftime("%b %d, %Y · %I:%M %p")
    await _notify(f"📅 Added: {title}\n{dt_str}", tags=["calendar"], priority=3)
    log.info("add_event id=%s title=%r dt=%s", event_id, title, dt)
    return (
        f"✅ Event added (ID: {event_id})\n"
        f"  📅 {title}\n"
        f"  🕐 {dt_str}\n"
        f"  ⏰ You'll get a reminder 15 minutes before."
    )


async def list_events(upcoming_only: bool = True) -> str:
    """
    List calendar events.

    Args:
        upcoming_only: If True, only show future events. Default True.

    Returns:
        Formatted list of events.
    """
    docs = await calendar_repo.get_events(upcoming_only=upcoming_only)
    if not docs:
        return f"📅 No {'upcoming ' if upcoming_only else ''}events found."
    lines = [f"📅 {'Upcoming' if upcoming_only else 'All'} events ({len(docs)}):"]
    for d in docs:
        dt: datetime = d["event_datetime"]
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt)
        dt_str = dt.strftime("%b %d, %Y · %I:%M %p")
        notes = f" — {d['notes']}" if d.get("notes") else ""
        lines.append(f"  [{d['_id'][:8]}] {d['title']} · {dt_str}{notes}")
    return "\n".join(lines)


async def mark_event_status(event_id: str, status: str, notes: str = "") -> str:
    """
    Mark a calendar event with a completion status.

    Args:
        event_id: The full ID returned when the event was added.
        status: attended | fulfilled | canceled | missed | rescheduled
        notes: Optional summary of what happened or was discussed.

    Returns:
        Confirmation string.
    """
    updates: dict = {"status": status}
    if notes:
        updates["outcome_notes"] = notes
    ok = await calendar_repo.update_event(event_id, **updates)
    if not ok:
        return f"❌ Event {event_id[:8]} not found."
    label = status.capitalize()
    await _notify(f"📅 {label}: event {event_id[:8]}", tags=["white_check_mark"], priority=2)
    return f"✅ Event {event_id[:8]} marked as {status}."


async def delete_event(event_id: str) -> str:
    """
    Delete a calendar event by its ID.

    Args:
        event_id: The full ID returned when the event was added.

    Returns:
        Confirmation string.
    """
    ok = await calendar_repo.delete_event(event_id)
    if not ok:
        return f"❌ Event {event_id[:8]} not found."
    return f"🗑️ Event {event_id[:8]} deleted."


# ── LangChain tool wrappers (used by workflow.py direct_tools) ────────────────
add_event_lc    = tool(add_event)
list_events_lc  = tool(list_events)
delete_event_lc = tool(delete_event)
