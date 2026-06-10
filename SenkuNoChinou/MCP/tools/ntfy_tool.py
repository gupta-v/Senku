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
_NTFY_TOKEN = os.getenv("NTFY_TOKEN", "")
_DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL", "")
_RETRY_DELAYS = (5.0, 15.0, 30.0)  # backoff on 429

_USE_NTFY = os.getenv("USE_NTFY", "false").lower() == "true"
_USE_DC = os.getenv("USE_DC", "false").lower() == "true"
# both false is a mistake — fall back to DC
_EFF_NTFY = _USE_NTFY
_EFF_DC = _USE_DC if (_USE_NTFY or _USE_DC) else True

# Priority → Discord embed colour (decimal)
_DISCORD_COLORS = {1: 0x95a5a6, 2: 0x95a5a6, 3: 0x3498db, 4: 0xe67e22, 5: 0xe74c3c}


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


async def _post_discord(title: str, message: str, priority: int, url: str = "") -> None:
    color = _DISCORD_COLORS.get(priority, 0x3498db)
    embed: dict = {"title": title, "description": message, "color": color}
    if url:
        embed["url"] = url
    payload: dict = {"embeds": [embed]}
    async with httpx.AsyncClient() as client:
        response = await client.post(_DISCORD_WEBHOOK, json=payload, timeout=10)
        response.raise_for_status()


async def send_notification(
    message: str,
    title: str = "Senku Reporting",
    priority: Literal[1, 2, 3, 4, 5] = 3,
    tags: list[str] = [],
    url: str = "",
) -> str:
    """
    Send a push notification to the owner's phone via Discord or ntfy.

    Description: Pushes a notification to the owner. Uses Discord webhook if
    configured, otherwise falls back to ntfy. Use to alert the user about
    research findings, reminders, events, price drops, or anything worth
    immediate attention.

    Args:
        message: Notification body text.
        title: Notification title. Default "Senku Reporting".
        priority: 1=min, 2=low, 3=default, 4=high, 5=urgent.
        tags: Emoji tag names shown on notification (ntfy only).
        url: Optional click-action URL. Opens when notification is tapped.

    Returns:
        Confirmation string or error message.
    """
    results: list[str] = []

    if _EFF_DC:
        try:
            await _post_discord(title, message, priority, url)
            results.append("Discord: sent")
        except Exception as e:
            results.append(f"Discord: failed ({e})")

    if _EFF_NTFY:
        headers = {"Title": title, "Priority": str(priority)}
        if tags:
            headers["Tags"] = ",".join(tags)
        if url:
            headers["Click"] = url
        try:
            await _post_ntfy(f"{_NTFY_BASE}/{_TOPIC}", message.encode("utf-8"), headers)
            results.append(f"ntfy({_TOPIC}): sent")
        except Exception as e:
            results.append(f"ntfy: failed ({e})")

    return " | ".join(results)


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
    yt_url = f"https://music.youtube.com/watch?v={video_id}"

    results: list[str] = []

    if _EFF_DC:
        try:
            await _post_discord(f"♪ {label}", "Tap the link to play in YouTube Music.", 3, yt_url)
            results.append("Discord: sent")
        except Exception as e:
            results.append(f"Discord: failed ({e})")

    if _EFF_NTFY:
        ascii_label = label.encode("ascii", errors="ignore").decode()
        headers = {
            "Title": f"Now Playing: {ascii_label}",
            "Priority": "3",
            "Tags": "musical_note",
            "Click": yt_url,
        }
        try:
            await _post_ntfy(f"{_NTFY_BASE}/{_TOPIC}", b"Tap to play in YouTube Music", headers)
            results.append(f"ntfy({_TOPIC}): sent")
        except Exception as e:
            results.append(f"ntfy: failed ({e})")

    return f"Sent to phone: {label}. Tap the notification to play. | " + " | ".join(results)


ntfy_lc_tool = tool(send_notification, args_schema=NtfyInput)
play_music_link_lc_tool = tool(play_music_link)
