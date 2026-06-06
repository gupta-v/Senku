"""
Journal / notes tools — add, read, edit entries.
Auto-sends ntfy on every write.

Raw async functions registered by journal_server.py (fastmcp).
LangChain wrappers at the bottom used directly by workflow.py.
"""
import asyncio
import logging
from datetime import datetime

from langchain.tools import tool

from SenkuNoChinou.MCP.tools.ntfy_tool import send_notification
from SenkuNoChinou.repositories import journal_repo

log = logging.getLogger("senku.tools.journal")


async def _notify(message: str, title: str = "Senku · Journal", priority: int = 2, tags: list[str] | None = None) -> None:
    await asyncio.to_thread(send_notification, message, title, priority, tags or [])


async def add_journal(content: str, mood: str = "", tags: str = "") -> str:
    """
    Add a new journal or notes entry.

    Args:
        content: The journal text to save.
        mood: Optional mood label (e.g. 'productive', 'tired', 'excited').
        tags: Comma-separated tags for filtering later (e.g. 'work,coding,ideas').

    Returns:
        Confirmation string with entry ID.
    """
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    entry_id = await journal_repo.insert_entry(content, mood, tag_list)
    date_str = datetime.utcnow().strftime("%b %d, %Y")
    mood_str = f" · {mood}" if mood else ""
    await _notify(f"📔 Journal saved{mood_str} — {date_str}", tags=["memo"])
    log.info("add_journal id=%s chars=%d", entry_id, len(content))
    return f"✅ Journal entry saved (ID: {entry_id})\n  📔 {date_str}{mood_str}"


async def read_journal(days: int = 7, tag: str = "") -> str:
    """
    Read recent journal entries.

    Args:
        days: How many days back to look. Default 7.
        tag: Filter entries by a specific tag (optional).

    Returns:
        Formatted journal entries, newest first.
    """
    docs = await journal_repo.get_entries(days=days, tag=tag)
    if not docs:
        return f"📔 No journal entries found for last {days} days" + (f" with tag '{tag}'" if tag else "") + "."
    lines = [f"📔 Journal — last {days} days ({len(docs)} entries):"]
    for d in docs:
        ts: datetime = d["created_at"]
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        date_str = ts.strftime("%b %d, %Y %I:%M %p")
        mood_str = f" [{d['mood']}]" if d.get("mood") else ""
        tags_str = f" #{' #'.join(d['tags'])}" if d.get("tags") else ""
        lines.append(f"\n  [{d['_id'][:8]}] {date_str}{mood_str}{tags_str}")
        for line in d["content"].splitlines():
            lines.append(f"    {line}")
    return "\n".join(lines)


async def edit_journal(entry_id: str, content: str) -> str:
    """
    Edit an existing journal entry's content.

    Args:
        entry_id: The full ID returned when the entry was added.
        content: The new full content to replace the existing entry.

    Returns:
        Confirmation string.
    """
    ok = await journal_repo.update_entry(entry_id, content)
    if not ok:
        return f"❌ Journal entry {entry_id[:8]} not found."
    await _notify(f"✏️ Journal updated — {entry_id[:8]}", tags=["pencil2"])
    return f"✅ Journal entry {entry_id[:8]} updated."


# ── LangChain tool wrappers (used by workflow.py direct_tools) ────────────────
add_journal_lc   = tool(add_journal)
read_journal_lc  = tool(read_journal)
edit_journal_lc  = tool(edit_journal)
