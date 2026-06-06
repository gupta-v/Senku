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

_INTERVAL_SECONDS = 60  # check every minute


async def _fire_reminders() -> None:
    """Check for events needing a 15-min reminder and send ntfy."""
    try:
        due = await calendar_repo.get_events_needing_reminder()
        for event in due:
            title = event.get("title", "Event")
            dt: datetime = event["event_datetime"]
            if isinstance(dt, str):
                dt = datetime.fromisoformat(dt)
            dt_str = dt.strftime("%I:%M %p")
            message = f"⏰ 15 min: {title} at {dt_str}"
            log.info("reminder ntfy event_id=%s title=%r", event["_id"][:8], title)
            await asyncio.to_thread(
                send_notification,
                message,
                "Senku · Reminder",
                4,           # high priority
                ["alarm_clock"],
            )
            await calendar_repo.mark_reminder_sent(event["_id"])
    except Exception as exc:
        log.error("scheduler error: %s", exc)


async def run_scheduler() -> None:
    """Infinite loop — call from asyncio.create_task() in lifespan."""
    log.info("calendar scheduler started — interval=%ds", _INTERVAL_SECONDS)
    while True:
        await _fire_reminders()
        await asyncio.sleep(_INTERVAL_SECONDS)
