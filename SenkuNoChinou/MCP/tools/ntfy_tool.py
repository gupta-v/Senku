import asyncio
import os
from typing import Literal

import httpx
from dotenv import load_dotenv
from langchain.tools import tool

from SenkuNoChinou.models.mcpSchema import NtfyInput

load_dotenv()

_TOPIC = os.getenv("NTFY_TOPIC", "senku-hokoku")
_NTFY_BASE = "https://ntfy.sh"
_NTFY_TOKEN = os.getenv("NTFY_TOKEN", "")  # set to avoid shared-IP rate limits on Render
_RETRY_DELAYS = (5.0, 15.0, 30.0)  # backoff on 429


async def _post_ntfy(url: str, content: bytes, headers: dict) -> httpx.Response:
    if _NTFY_TOKEN:
        headers = {**headers, "Authorization": f"Bearer {_NTFY_TOKEN}"}
    async with httpx.AsyncClient() as client:
        for delay in (*_RETRY_DELAYS, None):
            response = await client.post(url, content=content, headers=headers, timeout=10)
            if response.status_code != 429 or delay is None:
                response.raise_for_status()
                return response
            wait = float(response.headers.get("Retry-After", delay))
            await asyncio.sleep(wait)
    raise RuntimeError("unreachable")


async def send_notification(
    message: str,
    title: str = "Senku Reporting",
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
        await _post_ntfy(f"{_NTFY_BASE}/{_TOPIC}", message.encode("utf-8"), headers)
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
        video_id: YouTube video ID from search_music results (e.g. dQw4w9WgXcQ). NOT a full URL.
        title: Track title shown in the notification.
        artist: Artist name shown in the notification.

    Returns:
        Confirmation string or error.
    """
    # strip label prefix if model copied "VideoID: xxx" instead of bare "xxx"
    if ":" in video_id and not video_id.startswith("http"):
        video_id = video_id.split(":")[-1]
    # strip full URL if model passed it instead of bare ID
    if "watch?v=" in video_id:
        video_id = video_id.split("watch?v=")[-1].split("&")[0]
    video_id = video_id.strip()
    if not video_id:
        return "Error: video_id is empty. Call search_music first and pass the VideoID field."

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
        await _post_ntfy(f"{_NTFY_BASE}/{_TOPIC}", b"Tap to play in YouTube Music", headers)
        return f"Sent to phone: {label}. Tap the notification to play."
    except Exception as e:
        return f"Failed to send: {e}"


ntfy_lc_tool = tool(send_notification, args_schema=NtfyInput)
play_music_link_lc_tool = tool(play_music_link)
