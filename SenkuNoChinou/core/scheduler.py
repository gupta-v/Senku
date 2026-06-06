"""
Background scheduler — fires ntfy reminders 15 minutes before calendar events.
Runs as a single asyncio task started in main.py's lifespan.
"""
import asyncio
import logging
from datetime import datetime

from SenkuNoChinou.MCP.tools.ntfy_tool import send_notification
from SenkuNoChinou.repositories import calendar_repo

log = logging.getLogger("senku.scheduler")

_INTERVAL_SECONDS = 60   # check every minute
_MAX_BACKOFF = 600       # 10 min cap on error backoff


async def _fire_reminders() -> None:
    """Check for events needing a 15-min reminder and send ntfy."""
    due = await calendar_repo.get_events_needing_reminder()
    for event in due:
        title = event.get("title", "Event")
        dt: datetime = event["event_datetime"]
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt)
        dt_str = dt.strftime("%I:%M %p")
        message = f"⏰ 15 min: {title} at {dt_str}"
        log.info("reminder ntfy event_id=%s title=%r", event["_id"][:8], title)
        await send_notification(
            message,
            "Senku · Reminder",
            4,           # high priority
            ["alarm_clock"],
        )
        await calendar_repo.mark_reminder_sent(event["_id"])


async def run_scheduler() -> None:
    """Infinite loop — call from asyncio.create_task() in lifespan."""
    log.info("calendar scheduler started — interval=%ds", _INTERVAL_SECONDS)
    fail_count = 0
    while True:
        try:
            await _fire_reminders()
            fail_count = 0
        except Exception as exc:
            fail_count += 1
            backoff = min(30 * (2 ** (fail_count - 1)), _MAX_BACKOFF)
            log.error("scheduler error (attempt %d, backoff=%ds): %s", fail_count, backoff, exc)
            await asyncio.sleep(backoff)
            continue
        await asyncio.sleep(_INTERVAL_SECONDS)
