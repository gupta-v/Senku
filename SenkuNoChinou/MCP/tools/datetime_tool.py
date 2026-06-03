from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv
from langchain.tools import tool

from SenkuNoChinou.models.mcpSchema import DatetimeInput

load_dotenv()


def get_datetime(timezone: str = "Asia/Kolkata") -> str:
    """
    Get the current date and time for a given timezone.

    Args:
        timezone: Timezone name. Default Asia/Kolkata (IST).

    Returns:
        Current datetime string with timezone info.
    """
    try:
        tz = ZoneInfo(timezone)
    except ZoneInfoNotFoundError:
        return f"Unknown timezone '{timezone}'. Use IANA names like Asia/Kolkata, UTC, America/New_York."
    now = datetime.now(tz)
    return now.strftime(f"%A, %d %B %Y %I:%M %p %Z (UTC%z)")


datetime_lc_tool = tool(get_datetime, args_schema=DatetimeInput)
