import os
from typing import Literal

import httpx
from dotenv import load_dotenv
from langchain.tools import tool

from SenkuNoChinou.models.mcpSchema import NtfyInput

load_dotenv()

_TOPIC = os.getenv("NTFY_TOPIC", "senku-hokoku")
_NTFY_BASE = "https://ntfy.sh"


async def send_notification(
    message: str,
    title: str = "Senku",
    priority: Literal[1, 2, 3, 4, 5] = 3,
    tags: list[str] = [],
    url: str = "",
) -> str:
    """
    Send a push notification to the owner's phone via ntfy.

    Description: Pushes a notification to the subscribed ntfy topic.
    Use to alert the user about research findings, reminders, events,
    price drops, or anything worth immediate attention.

    Args:
        message: Notification body text.
        title: Notification title. Default "Senku".
        priority: 1=min, 2=low, 3=default, 4=high, 5=urgent.
        tags: Emoji tag names shown on notification (e.g. ["robot", "mag", "warning"]).
        url: Optional click-action URL. Opens when notification is tapped.

    Returns:
        Confirmation string or error message.
    """
    headers = {
        "Title": title,
        "Priority": str(priority),
    }
    if tags:
        headers["Tags"] = ",".join(tags)
    if url:
        headers["Click"] = url

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{_NTFY_BASE}/{_TOPIC}",
                content=message.encode("utf-8"),
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()
        return f"Notification sent to {_TOPIC}."
    except Exception as e:
        return f"Failed to send notification: {e}"


async def play_music_link(video_id: str, title: str = "", artist: str = "") -> str:
    """
    Push a tap-to-play YouTube Music notification to the owner's phone.

    Description: Sends a notification with a YouTube Music deep link as the
    click action. User taps it — YouTube Music app opens and plays the track.
    Use this as the final step after search_music finds a match.

    Args:
        video_id: YouTube video ID from search_music results.
        title: Track title shown in the notification.
        artist: Artist name shown in the notification.

    Returns:
        Confirmation string or error.
    """
    label = f"{title} - {artist}".strip(" -") if (title or artist) else video_id
    label = label.encode("ascii", errors="ignore").decode()
    yt_url = f"https://music.youtube.com/watch?v={video_id}"
    headers = {
        "Title": f"Now Playing: {label}",
        "Priority": "3",
        "Tags": "musical_note",
        "Click": yt_url,
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{_NTFY_BASE}/{_TOPIC}",
                content="Tap to play in YouTube Music".encode("utf-8"),
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()
        return f"Sent to phone: {label}. Tap the notification to play."
    except Exception as e:
        return f"Failed to send: {e}"


ntfy_lc_tool = tool(send_notification, args_schema=NtfyInput)
play_music_link_lc_tool = tool(play_music_link)
