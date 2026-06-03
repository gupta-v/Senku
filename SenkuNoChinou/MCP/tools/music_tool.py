import ctypes
import json
import subprocess
import logging

from dotenv import load_dotenv
from langchain.tools import tool
from ytmusicapi import YTMusic

from SenkuNoChinou.models.mcpSchema import (
    PlayMusicInput,
    PlayByNumberInput,
    PlayByIdInput,
    SearchMusicInput,
    VolumeInput,
)

load_dotenv()
logging.getLogger("LiteLLM").setLevel(logging.ERROR)

_PIPE = r"\\.\pipe\senku-mpvsocket"
_yt = YTMusic()
_mpv_proc: subprocess.Popen | None = None
_current_track: dict = {}
_search_results: list[dict] = []   # last search results, indexed by user's 1-based number
_queue_index: int = -1              # position in _search_results currently playing
_history: list[dict] = []           # stack of previously played tracks


# ── IPC helpers ────────────────────────────────────────────────────────────────

def _send(command: list) -> bool:
    kernel32 = ctypes.windll.kernel32
    GENERIC_WRITE, OPEN_EXISTING = 0x40000000, 3
    handle = kernel32.CreateFileW(_PIPE, GENERIC_WRITE, 0, None, OPEN_EXISTING, 0, None)
    if handle == ctypes.c_void_p(-1).value:
        return False
    msg = (json.dumps({"command": command}) + "\n").encode("utf-8")
    written = ctypes.c_ulong(0)
    kernel32.WriteFile(handle, msg, len(msg), ctypes.byref(written), None)
    kernel32.CloseHandle(handle)
    return True


# ── Core playback ──────────────────────────────────────────────────────────────

def _play_track(track: dict, queue_pos: int = -1, push_history: bool = True) -> str:
    global _mpv_proc, _current_track, _queue_index, _history
    if push_history and _current_track:
        _history.append(_current_track)

    video_id = track.get("videoId")
    if not video_id:
        return "Track has no videoId — cannot play."

    title  = track.get("title", "Unknown")
    artist = ", ".join(a["name"] for a in (track.get("artists") or [])) or "Unknown"
    yt_url = f"https://music.youtube.com/watch?v={video_id}"

    if _mpv_proc and _mpv_proc.poll() is None:
        _mpv_proc.terminate()

    try:
        _mpv_proc = subprocess.Popen(
            [
                "mpv", "--no-video", "--no-terminal",
                f"--input-ipc-server={_PIPE}",
                "--ytdl-format=bestaudio/best",
                yt_url,
            ],
            creationflags=subprocess.CREATE_NO_WINDOW,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        return "mpv not found. Ensure mpv is installed and in PATH."

    import time; time.sleep(2)
    if _mpv_proc.poll() is not None:
        return "mpv exited immediately. Check that mpv is installed and the video ID is valid."

    _current_track = {"title": title, "artist": artist, "video_id": video_id}
    _queue_index = queue_pos
    return f"▶ {title} — {artist}"


# ── Tools ──────────────────────────────────────────────────────────────────────

def search_music(query: str, limit: int | str = 5, search_type: str = "songs") -> str:
    """
    Search YouTube Music and return top results without playing.

    Description: Returns a numbered list of matching tracks. Results are
    stored — use play_by_number to play a specific result, or next_music
    to advance through them. Use search_type="videos" for live performances.

    Args:
        query: Song name, artist, album, or any search term.
        limit: Number of results to return. Default 5, max 20.
        search_type: "songs" for studio tracks, "videos" for live/concerts, "all" for everything.

    Returns:
        Numbered list of matching tracks.
    """
    global _search_results
    limit = max(3, min(int(limit), 20))
    yt_filter = None if search_type == "all" else search_type
    results = _yt.search(query, filter=yt_filter, limit=limit)
    if not results:
        return f"No results found for '{query}'."

    _search_results = results[:limit]
    lines = []
    for i, t in enumerate(_search_results, 1):
        title       = t.get("title", "Unknown")
        artist      = ", ".join(a["name"] for a in (t.get("artists") or [])) or "Unknown"
        album       = t.get("album", {}).get("name", "") if t.get("album") else ""
        dur         = t.get("duration", "")
        views       = t.get("views", "") or t.get("viewCount", "")
        result_type = t.get("resultType", "")

        video_id    = t.get("videoId", "")
        line = f"{i}. {title}"
        line += f"\n   Artist  : {artist}"
        if album:
            line += f"\n   Album   : {album}"
        if video_id:
            line += f"\n   VideoID : {video_id}"
        meta = []
        if dur:
            meta.append(f"⏱ {dur}")
        if views:
            meta.append(f"👁 {views}")
        if result_type:
            meta.append(f"[{result_type}]")
        if meta:
            line += f"\n   {' · '.join(meta)}"
        lines.append(line)
    return "\n\n".join(lines)


def play_by_number(number: int) -> str:
    """
    Play a track by its number from the last search results.

    Args:
        number: Track number shown in the last search_music results.

    Returns:
        Now-playing string or error.
    """
    if not _search_results:
        return "No search results in memory. Run search_music first."
    if number < 1 or number > len(_search_results):
        return f"Invalid number. Last search had {len(_search_results)} results."
    return _play_track(_search_results[number - 1], queue_pos=number - 1)


def play_by_id(video_id: str) -> str:
    """
    Play a track directly by its YouTube video ID.

    Description: Most reliable way to play a specific track. Pass the VideoID
    from search_music results. No shared state needed.

    Args:
        video_id: YouTube video ID shown in search_music results (e.g. dQw4w9WgXcQ).

    Returns:
        Now-playing string or error.
    """
    result = _play_track({"videoId": video_id}, queue_pos=-1)
    if result.startswith("▶") or "exited" not in result:
        return f"Playback started for video {video_id}. Task complete — do not call any more music tools."
    return result


def next_music() -> str:
    """
    Play the next recommended track based on what's currently playing.

    Description: Fetches YouTube Music's "up next" recommendation for the
    current track and plays it — same as YouTube autoplay/radio. No
    arguments needed.

    Returns:
        Now-playing string or error.
    """
    if not _current_track or not _current_track.get("video_id"):
        return "Nothing playing. Use play_music or play_by_number first."
    try:
        playlist = _yt.get_watch_playlist(videoId=_current_track["video_id"])
        tracks = playlist.get("tracks", [])
        # index 0 is the current track — take index 1 (first recommendation)
        next_tracks = [t for t in tracks if t.get("videoId") != _current_track["video_id"]]
        if not next_tracks:
            return "No recommendations found for current track."
        return _play_track(next_tracks[0], queue_pos=-1)
    except Exception as e:
        return f"Failed to fetch recommendations: {e}"


def previous_music() -> str:
    """
    Play the previously played track.

    Description: Goes back one step in play history. Works across
    play_music, play_by_number, and next_music calls.

    Returns:
        Now-playing string or error.
    """
    if not _history:
        return "No play history."
    prev = _history.pop()
    return _play_track(prev, queue_pos=-1, push_history=False)


def play_music(query: str) -> str:
    """
    Search YouTube Music and instantly play the best match.

    Args:
        query: Song name, artist, album, or any search term.

    Returns:
        Now-playing string or error.
    """
    global _search_results
    live_keywords = {"live", "concert", "performance", "session", "festival"}
    yt_filter = "videos" if any(k in query.lower() for k in live_keywords) else "songs"
    results = _yt.search(query, filter=yt_filter, limit=5)
    if not results:
        results = _yt.search(query, filter=None, limit=5)
    if not results:
        return f"No results for '{query}'."
    _search_results = results
    return _play_track(results[0], queue_pos=0)


def pause_music() -> str:
    """Pause current playback."""
    return "Paused." if _send(["cycle", "pause"]) else "Nothing playing."


def resume_music() -> str:
    """Resume paused playback."""
    return "Resumed." if _send(["set_property", "pause", False]) else "Nothing playing."


def stop_music() -> str:
    """Stop playback and clear queue."""
    global _mpv_proc, _current_track, _queue_index
    if _mpv_proc and _mpv_proc.poll() is None:
        _mpv_proc.terminate()
        _mpv_proc = None
        _current_track = {}
        _queue_index = -1
        return "Stopped."
    return "Nothing playing."


def now_playing() -> str:
    """Return the currently playing track."""
    if _mpv_proc and _mpv_proc.poll() is None and _current_track:
        pos = f"  (#{_queue_index + 1} in queue)" if _queue_index >= 0 else ""
        return f"▶ {_current_track['title']} — {_current_track['artist']}{pos}"
    return "Nothing playing."


def set_volume(level: int) -> str:
    """
    Set playback volume.

    Args:
        level: Volume 0-100.

    Returns:
        Confirmation string.
    """
    level = max(0, min(100, level))
    return f"Volume set to {level}." if _send(["set_property", "volume", level]) else "Nothing playing."


# ── LangChain tools ────────────────────────────────────────────────────────────

music_search_lc_tool  = tool(search_music,   args_schema=SearchMusicInput)
music_play_lc_tool    = tool(play_music,      args_schema=PlayMusicInput)
music_playn_lc_tool   = tool(play_by_number,  args_schema=PlayByNumberInput)
music_playid_lc_tool  = tool(play_by_id,      args_schema=PlayByIdInput)
music_next_lc_tool    = tool(next_music)
music_prev_lc_tool    = tool(previous_music)
music_pause_lc_tool   = tool(pause_music)
music_resume_lc_tool  = tool(resume_music)
music_stop_lc_tool    = tool(stop_music)
music_nowplay_lc_tool = tool(now_playing)
music_volume_lc_tool  = tool(set_volume,      args_schema=VolumeInput)
