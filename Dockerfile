FROM python:3.12-slim

# ffmpeg required by faster-whisper for audio decoding
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install deps first (layer cache)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

# Bake Whisper model into image at build time — no cold-start download
RUN uv run python -c "\
from huggingface_hub import snapshot_download; \
snapshot_download(\
    repo_id='Systran/faster-whisper-small', \
    local_dir='SenkuNoChinou/models/stt_models/small', \
    ignore_patterns=['*.msgpack', '*.h5', 'flax_model*', 'tf_model*', '.gitattributes', 'README.md'] \
)"

EXPOSE 8000

# Render injects $PORT — fall back to 8000 locally
CMD uv run uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
