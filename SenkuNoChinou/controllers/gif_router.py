"""
GIF API router — serves GIF metadata and RGB565 frames to the ESP32.

Endpoints:
  GET /senku/gif/list                  — list available GIFs
  GET /senku/gif/{name}/info           — frame count + delay
  GET /senku/gif/{name}/frame/{index}  — single frame as raw RGB565 binary
  GET /senku/gif/{name}/stream         — all frames as multipart/x-mixed-replace stream
"""
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response, StreamingResponse

from SenkuNoChinou.services.gif_service import (
    KNOWN_GIFS,
    get_frame_rgb565,
    get_gif_info,
    iter_frames_rgb565,
)

log = logging.getLogger("senku.gif")

gif_router = APIRouter(prefix="/senku/gif", tags=["gif"])


@gif_router.get("/list")
async def list_gifs():
    """Return names of all available GIFs."""
    return {"gifs": sorted(KNOWN_GIFS)}


@gif_router.get("/{name}/info")
async def gif_info(name: str):
    """
    Return metadata: frame count, per-frame delay, and display dimensions.
    The ESP32 calls this once to know how many frames to fetch and how fast to play.
    """
    try:
        return get_gif_info(name)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


@gif_router.get("/{name}/frame/{index}")
async def gif_frame(name: str, index: int):
    """
    Return a single frame as raw RGB565 big-endian binary (160×128×2 = 40960 bytes).
    Header X-Delay-Ms carries the frame's display duration in milliseconds.
    """
    try:
        delay_ms, data = get_frame_rgb565(name, index)
        return Response(
            content=data,
            media_type="application/octet-stream",
            headers={"X-Delay-Ms": str(delay_ms), "X-Frame": str(index)},
        )
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except IndexError as e:
        raise HTTPException(404, str(e))


@gif_router.get("/{name}/stream")
async def gif_stream(name: str):
    """
    Stream all frames as multipart/x-mixed-replace.
    Each part boundary carries X-Delay-Ms and X-Frame headers.
    The ESP32 reads this once and plays the animation in a loop.

    Frame format per part:
      --frame\\r\\n
      X-Delay-Ms: <ms>\\r\\n
      X-Frame: <n>\\r\\n
      Content-Type: application/octet-stream\\r\\n
      Content-Length: <bytes>\\r\\n
      \\r\\n
      <raw RGB565 bytes>
    """
    try:
        get_gif_info(name)  # validate name early
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))

    def _generate():
        for i, delay_ms, data in iter_frames_rgb565(name):
            log.debug("gif_stream name=%s frame=%d delay=%d", name, i, delay_ms)
            header = (
                b"--frame\r\n"
                b"X-Delay-Ms: " + str(delay_ms).encode() + b"\r\n"
                b"X-Frame: " + str(i).encode() + b"\r\n"
                b"Content-Type: application/octet-stream\r\n"
                b"Content-Length: " + str(len(data)).encode() + b"\r\n"
                b"\r\n"
            )
            yield header + data + b"\r\n"

    return StreamingResponse(
        _generate(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )
