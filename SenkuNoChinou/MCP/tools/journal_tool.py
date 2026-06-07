"""
Journal / notes tools — add, read, edit entries.

Raw async functions registered by journal_server.py (fastmcp).
LangChain wrappers at the bottom used directly by workflow.py.
"""
import logging
import re
from datetime import datetime

from langchain.tools import tool

from SenkuNoChinou.repositories import journal_repo

_OID_RE = re.compile(r'^[0-9a-fA-F]{24}$')


async def _resolve_journal_id(entry_id_or_title: str) -> tuple[str, str] | str:
    """Return (id, title) or an error string."""
    if _OID_RE.match(entry_id_or_title):
        return entry_id_or_title, entry_id_or_title[:8]
    needle = entry_id_or_title.lower().strip()
    needle_norm = needle.replace(" ", "")

    def _match(title: str) -> bool:
        t = title.lower()
        return needle in t or (needle_norm and needle_norm in t.replace(" ", ""))

    docs = await journal_repo.get_entries(days=365)
    matches = [d for d in docs if _match(d.get("title", ""))]
    if not matches:
        titles = ", ".join(f"'{d.get('title', d['_id'][:8])}'" for d in docs[:5])
        return f"❌ No journal entry matches '{entry_id_or_title}'. Recent: {titles or 'none'}."
    if len(matches) > 1:
        titles = ", ".join(f"'{d.get('title', d['_id'][:8])}'" for d in matches)
        return f"❌ Multiple entries match '{entry_id_or_title}': {titles}. Be more specific."
    return matches[0]["_id"], matches[0].get("title", matches[0]["_id"][:8])

log = logging.getLogger("senku.tools.journal")


async def add_journal(title: str = "", content: str = "", mood: str = "", tags: str = "") -> str:
    """
    Add a new journal or notes entry.

    Args:
        title: Short title for the entry (3-6 words capturing the main theme).
        content: The journal text to save.
        mood: Optional mood label (e.g. 'reflective', 'excited', 'melancholic', 'curious').
        tags: Comma-separated tags for filtering later (max 5, e.g. 'sailing,escapism,happiness').

    Returns:
        Confirmation string with entry ID and title.
    """
    tag_list = [t.strip() for t in tags.split(",") if t.strip()][:5] if tags else []
    entry_id = await journal_repo.insert_entry(content, mood, tag_list, title)
    date_str = datetime.utcnow().strftime("%b %d, %Y")
    mood_str = f" · {mood}" if mood else ""
    title_str = f" '{title}'" if title else ""
    log.info("add_journal id=%s title=%r chars=%d", entry_id, title, len(content))
    return f"✅ Journal entry{title_str} saved (ID: {entry_id})\n  📔 {date_str}{mood_str}"


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
        title_str = f" | {d['title']}" if d.get("title") else ""
        mood_str = f" [{d['mood']}]" if d.get("mood") else ""
        tags_str = f" #{' #'.join(d['tags'])}" if d.get("tags") else ""
        lines.append(f"\n  [id:{d['_id']}] {date_str}{title_str}{mood_str}{tags_str}")
        for line in d["content"].splitlines():
            lines.append(f"    {line}")
    return "\n".join(lines)


async def edit_journal(entry_id: str, content: str) -> str:
    """
    Edit an existing journal entry's content.

    Args:
        entry_id: The full ID, OR a keyword/partial title of the entry.
        content: The new full content to replace the existing entry.

    Returns:
        Confirmation string.
    """
    resolved = await _resolve_journal_id(entry_id)
    if isinstance(resolved, str):
        return resolved
    real_id, label = resolved
    ok = await journal_repo.update_entry(real_id, content)
    if not ok:
        return f"❌ Journal entry '{label}' not found."
    return f"✅ Journal entry '{label}' updated."


# ── LangChain tool wrappers (used by workflow.py direct_tools) ────────────────
add_journal_lc   = tool(add_journal)
read_journal_lc  = tool(read_journal)
edit_journal_lc  = tool(edit_journal)
