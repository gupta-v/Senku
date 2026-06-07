"""
Calendar tools — add, list, delete events.
Scheduler handles 15-min reminders separately.

Raw async functions registered by calendar_server.py (fastmcp).
LangChain wrappers at the bottom used directly by workflow.py.
"""
import logging
import re
from datetime import datetime

from langchain.tools import tool

from SenkuNoChinou.repositories import calendar_repo

log = logging.getLogger("senku.tools.calendar")

_OID_RE = re.compile(r'^[0-9a-fA-F]{24}$')


def _parse_dt(dt_str: str) -> datetime:
    """Try common ISO-like formats."""
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse datetime: {dt_str!r}. Use YYYY-MM-DD HH:MM")


async def _resolve_event_id(event_id_or_name: str) -> tuple[str, str] | str:
    """Return (id, title) or an error string."""
    if _OID_RE.match(event_id_or_name):
        return event_id_or_name, event_id_or_name[:8]
    needle = event_id_or_name.lower().strip()
    needle_norm = needle.replace(" ", "")

    def _match(title: str) -> bool:
        t = title.lower()
        return needle in t or (needle_norm and needle_norm in t.replace(" ", ""))

    all_events = await calendar_repo.get_events(upcoming_only=False)
    matches = [d for d in all_events if _match(d["title"])]
    if not matches:
        titles = ", ".join(f"'{d['title']}'" for d in all_events[:5])
        return f"❌ No event matches '{event_id_or_name}'. Events: {titles or 'none'}."
    if len(matches) > 1:
        titles = ", ".join(f"'{d['title']}'" for d in matches)
        return f"❌ Multiple events match '{event_id_or_name}': {titles}. Be more specific."
    return matches[0]["_id"], matches[0]["title"]


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
    log.info("add_event id=%s title=%r dt=%s", event_id, title, dt)
    return (
        f"✅ Event added (ID: {event_id})\n"
        f"  📅 {title}\n"
        f"  🕐 {dt_str}\n"
        f"  ⏰ You'll get a reminder 15 minutes before."
    )


async def list_events(upcoming_only: str | bool = True) -> str:
    """
    List calendar events.

    Args:
        upcoming_only: If True (or "true"), only show future events. Default True.

    Returns:
        Formatted list of events.
    """
    if isinstance(upcoming_only, str):
        upcoming_only = upcoming_only.lower() not in ("false", "0", "no")
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
        lines.append(f"  [id:{d['_id']}] {d['title']} · {dt_str}{notes}")
    return "\n".join(lines)


async def mark_event_status(event_id: str, status: str, notes: str = "") -> str:
    """
    Mark a calendar event with a completion status.

    Args:
        event_id: The full ID, OR a keyword/partial title of the event.
        status: attended | fulfilled | canceled | missed | rescheduled
        notes: Optional summary of what happened or was discussed.

    Returns:
        Confirmation string.
    """
    resolved = await _resolve_event_id(event_id)
    if isinstance(resolved, str):
        return resolved
    real_id, label = resolved

    updates: dict = {"status": status}
    if notes:
        updates["outcome_notes"] = notes
    ok = await calendar_repo.update_event(real_id, **updates)
    if not ok:
        return f"❌ Event '{label}' not found."
    return f"✅ '{label}' marked as {status}."


async def delete_event(event_id: str) -> str:
    """
    Delete a calendar event by ID or keyword title.

    Args:
        event_id: The full ID, OR a keyword/partial title of the event.

    Returns:
        Confirmation string.
    """
    resolved = await _resolve_event_id(event_id)
    if isinstance(resolved, str):
        return resolved
    real_id, label = resolved

    ok = await calendar_repo.delete_event(real_id)
    if not ok:
        return f"❌ Event '{label}' not found."
    return f"🗑️ '{label}' deleted."


# ── LangChain tool wrappers (used by workflow.py direct_tools) ────────────────
add_event_lc    = tool(add_event)
list_events_lc  = tool(list_events)
delete_event_lc = tool(delete_event)
mark_event_status_lc = tool(mark_event_status)
