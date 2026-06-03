# SenkuNoChinou (千空の知能)

Senku's Intelligence — agentic AI personal assistant backend. JARVIS/EDITH style. Built with LangGraph, FastMCP, and Groq. Exposes a FastAPI backend with text and voice input.

## What it does

- Answers research questions via web search (Tavily), Wikipedia, and URL browsing (Jina)
- Searches YouTube Music and pushes tap-to-play notifications to your phone
- Fetches weather and current datetime
- Sends push notifications via ntfy.sh
- Maintains multi-turn conversation memory per session
- Transcribes voice input via Whisper (faster-whisper, runs locally on CPU)
- Traces all runs in LangSmith

## Architecture

Three specialised agents (gears) routed by intent:

| Gear | Domain | Tools |
|------|--------|-------|
| Gear Ichi (一) | Knowledge | Wikipedia, web search, URL browsing |
| Gear Ni (二) | Lifestyle | YouTube Music search, tap-to-play, weather, datetime |
| Gear San (三) | Action | Push notifications |

Each gear boots its own MCP servers, loads its system prompt via MCP, and runs as a LangGraph ReAct agent with filtered tools.

## Setup

```bash
# Install deps
uv sync

# Copy and fill env vars
cp .env.example .env
```

Required env vars:
```
GROQ_API_KEY=
ICHI_MODEL=llama-3.3-70b-versatile
NI_MODEL=llama3-groq-70b-8192-tool-use-preview
SAN_MODEL=llama-3.3-70b-versatile
TAVILY_API_KEY=
JINA_API_KEY=
NTFY_TOPIC=senku-hokoku
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=
LANGCHAIN_PROJECT=senku
```

Optional Whisper env vars (defaults shown):
```
WHISPER_MODEL=small
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
WHISPER_MODEL_DIR=          # defaults to SenkuNoChinou/models/stt_models/
```

## Whisper model

Place model files in `SenkuNoChinou/models/stt_models/<model_size>/`:
```
SenkuNoChinou/models/stt_models/small/
├── model.bin
├── config.json
├── tokenizer.json
└── vocabulary.json
```

Download from: https://huggingface.co/Systran/faster-whisper-small

## Run

```bash
# FastAPI server (primary):
uv run python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload --reload-dir SenkuNoChinou

# CLI app:
uv run python .\SenkuNoChinou\services\cli_app.py
```

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/senku/create-thread` | Create new conversation thread → `{ thread_id }` |
| POST | `/senku/respond` | Text input → text response |
| POST | `/senku/respond-stream` | Text input → SSE token stream |
| POST | `/senku/transcribe` | Audio file → transcript |
| POST | `/senku/stt-respond` | Audio file → transcript + text response |
| POST | `/senku/stt-respond-stream` | Audio file → transcript + SSE token stream |

Interactive docs at `http://localhost:8000/docs`.

### STT endpoints (multipart/form-data)

| Field | Type | Default |
|-------|------|---------|
| `audio` | file | — |
| `thread_id` | string | — |
| `language` | string | `en` |

`/stt-respond-stream` SSE format:
```
data: {"transcript": "..."}
data: {"token": "..."}
...
data: [DONE]
```

## Test individual MCP server

```bash
uv run fastmcp dev inspector SenkuNoChinou/MCP/servers/<name>_server.py
```

## Stack

Python 3.12 · uv · FastAPI · uvicorn · LangGraph · LangChain · LangSmith · FastMCP · langchain-mcp-adapters · ChatGroq · faster-whisper · Tavily · Jina · ntfy.sh · ytmusicapi
