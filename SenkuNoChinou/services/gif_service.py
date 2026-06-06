"""
GIF Service — resize GIF frames on-the-fly and serve as RGB565 binary
for the ESP32 ST7735 TFT display (160×128 landscape).
"""
from __future__ import annotations

import struct
from functools import lru_cache
from pathlib import Path
from typing import Iterator

from PIL import Image, ImageSequence, ImageOps

# ── paths ──────────────────────────────────────────────────────────────────
_GIF_DIR = Path(__file__).parent.parent / "gifs"

# ── display dimensions ─────────────────────────────────────────────────────
TFT_W = 160
TFT_H = 128

# ── known GIF names (without extension) ───────────────────────────────────
KNOWN_GIFS = {p.stem for p in _GIF_DIR.glob("*.gif")}


def _gif_path(name: str) -> Path:
    """Validate and return the path for a GIF by name (no extension needed)."""
    if name not in KNOWN_GIFS:
        raise FileNotFoundError(f"GIF '{name}' not found. Available: {sorted(KNOWN_GIFS)}")
    return _GIF_DIR / f"{name}.gif"


def _frame_to_rgb565(frame: Image.Image) -> bytes:
    """Convert a PIL frame to a raw RGB565 big-endian byte string (TFT_W × TFT_H × 2 bytes)."""
    # Crop to exact TFT dimensions while preserving aspect ratio, composite onto black
    bg = Image.new("RGB", (TFT_W, TFT_H), (0, 0, 0))
    resized = ImageOps.fit(frame.convert("RGBA"), (TFT_W, TFT_H), method=Image.Resampling.LANCZOS)
    bg.paste(resized, mask=resized.split()[3])  # alpha composite
    rgb = bg

    buf = bytearray(TFT_W * TFT_H * 2)
    pixels = list(rgb.getdata())
    for i, (r, g, b) in enumerate(pixels):
        rgb565 = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
        struct.pack_into(">H", buf, i * 2, rgb565)
    return bytes(buf)


# ── Cached GIF metadata ────────────────────────────────────────────────────
@lru_cache(maxsize=16)
def get_gif_info(name: str) -> dict:
    """
    Returns metadata about a GIF without decoding all frames:
      { "frames": int, "delay_ms": int, "width": int, "height": int }
    delay_ms is the average frame delay (default 100ms if not set).
    """
    path = _gif_path(name)
    img = Image.open(path)
    n_frames = getattr(img, "n_frames", 1)
    delays = []
    try:
        for frame in ImageSequence.Iterator(img):
            delays.append(frame.info.get("duration", 100))
    except EOFError:
        pass
    avg_delay = int(sum(delays) / len(delays)) if delays else 100
    return {
        "name": name,
        "frames": n_frames,
        "delay_ms": max(avg_delay, 40),  # cap at ~25fps
        "width": TFT_W,
        "height": TFT_H,
    }


def iter_frames_rgb565(name: str) -> Iterator[tuple[int, int, bytes]]:
    """
    Yields (frame_index, delay_ms, rgb565_bytes) for every frame in the GIF.
    Frames are resized to TFT_W × TFT_H on the fly.
    """
    path = _gif_path(name)
    img = Image.open(path)
    for i, frame in enumerate(ImageSequence.Iterator(img)):
        delay = frame.info.get("duration", 100)
        delay = max(delay, 40)
        yield i, delay, _frame_to_rgb565(frame)


def get_frame_rgb565(name: str, frame_index: int) -> tuple[int, bytes]:
    """
    Return (delay_ms, rgb565_bytes) for a specific frame (0-indexed).
    Decodes only up to the requested frame — use iter_frames_rgb565 for
    sequential streaming which is much more efficient.
    """
    path = _gif_path(name)
    img = Image.open(path)
    for i, frame in enumerate(ImageSequence.Iterator(img)):
        if i == frame_index:
            delay = frame.info.get("duration", 100)
            return max(delay, 40), _frame_to_rgb565(frame)
    raise IndexError(f"Frame {frame_index} out of range for '{name}'")
