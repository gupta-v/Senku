# Senku

Personal AI assistant backend — JARVIS/EDITH style. Stateful multi-turn conversations, tool orchestration, voice input, and a physical desk bot that reacts in real time.

Built in two phases:

| Phase | Project | What it is |
|-------|---------|------------|
| **I — Chinou** (知能) | `SenkuNoChinou/` | Python backend: FastAPI + LangGraph + MCP. The brain. |
| **II — Bunshin** (分身) | `SenkNoBunshin/` | ESP32 firmware: TFT display, GIF emotion states, touch, WiFi SSE. The body. |

---

## Features

- **Research** — web search (Tavily), Wikipedia, browse any URL (Jina)
- **Productivity** — todos, calendar events with 15-min push reminders, journal entries
- **Lifestyle** — YouTube Music search + tap-to-play via phone notification, weather, datetime
- **Notifications** — push alerts to phone via ntfy.sh
- **Voice** — Groq Whisper API (`whisper-large-v3-turbo`), no local model
- **Memory** — multi-turn conversation memory per thread (MemorySaver checkpointer)
- **Observability** — full LangSmith tracing, every run linked to a thread
- **Edge device** — Senku desk bot displays emotion GIFs and now-playing over WiFi SSE

---

## Architecture

### Phase I — SenkuNoChinou

```
FastAPI (port 8000)
├── POST /senku/respond           ← text in, text out
├── POST /senku/respond-stream    ← text in, SSE token stream
├── POST /senku/stt-respond       ← audio in (Groq Whisper), text out
├── POST /senku/stt-respond-stream
├── POST /senku/create-thread
└── POST /senku/transcribe

LangGraph workflow (stateful, MemorySaver)
├── GearZero   — intent router
├── gear_ichi  — knowledge agent   ←→ ichi_server :8081
├── gear_ni    — productivity agent ←→ ni_server   :8082
├── gear_san   — lifestyle agent   ←→ san_server   :8083
├── gear_go    — action agent      ←→ go_server    :8084
└── GearYon    — verifier + synthesizer (no tools)

FastMCP (4 in-process HTTP servers, ports 8081–8084)
MongoDB Atlas (Beanie ODM — todos, events, journal)
Background scheduler (asyncio — calendar reminders every 60s)
```

### Phase II — SenkNoBunshin (ESP32)

- Connects to FastAPI via WiFi SSE
- TFT display (160×128) renders GIF emotion states: idle, happy, curious, alert
- Displays now-playing track from Senku
- Touch events (planned)

---

## Workflow

Every request flows through a fixed graph:

```
User message
     │
     ▼
┌──────────┐
│ GearZero │  Reads last 3 messages → structured output → gear name
└─────┬────┘
      │  ichi | ni | san | go
      ▼
┌───────────────────────────────────────────────┐
│  gear_ichi   gear_ni   gear_san   gear_go     │
│  Knowledge   Produc.   Lifestyle  Action      │
│  (ReAct agent with filtered MCP tools)        │
└──────────────────────┬────────────────────────┘
                       │
                       ▼
              ┌─────────────┐
              │  GearYon    │  Verifies task completion (structured output)
              │  Verifier   │  Synthesizes display-ready response
              └──────┬──────┘
                     │
          fulfilled? └─ yes ──► END  (stream response to client)
                     └─ no  ──► retry → target gear  (max 2 retries)
```

### Nodes

| Node | Role | Model |
|------|------|-------|
| `GearZero` | Classifies intent → `ichi \| ni \| san \| go`. Structured output (`RouteDecision`). Looks at last 3 messages for follow-up context. | `ICHI_MODEL` |
| `gear_ichi` | ReAct agent. Wikipedia, Tavily search, Jina URL browse. | `ICHI_MODEL` |
| `gear_ni` | ReAct agent. Todos, calendar events, journal, datetime. | `NI_MODEL` |
| `gear_san` | ReAct agent. YouTube Music, weather, datetime, search. | `SAN_MODEL` |
| `gear_go` | ReAct agent. ntfy.sh push notifications. | `GO_MODEL` |
| `GearYon` | No tools. Structured output (`YonVerdict`): `fulfilled` bool + `target_gear`. Concurrently runs verdict + response synthesis. | `YON_MODEL` |

GearYon runs two LLM calls **in parallel** via `asyncio.gather`: one for the structured verdict, one for the final text response.

### MCP Servers

Four FastMCP HTTP servers run **in-process** inside the FastAPI app (no subprocesses). Gears connect via `streamable_http`:

| Server | Port | Tools |
|--------|------|-------|
| `ichi_server` | 8081 | `ask_wikipedia`, `internet_search`, `browse_url` |
| `ni_server` | 8082 | `get_datetime`, `add_todo`, `list_todos`, `complete_todo`, `edit_todo`, `add_event`, `list_events`, `delete_event`, `mark_event_status`, `add_journal`, `read_journal`, `edit_journal` |
| `san_server` | 8083 | `search_music`, `play_music_link`, `get_datetime`, `get_weather`, `internet_search`, `ask_wikipedia` |
| `go_server` | 8084 | `send_notification` |

---

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- MongoDB Atlas cluster (free tier works)
- Groq API key — LLM inference + Whisper STT
- Tavily API key — web search
- Jina API key(s) — URL reader
- ntfy.sh topic — push notifications
- LangSmith API key — tracing (optional but recommended)

---

## Setup

```bash
# Install deps
uv sync

# Configure env vars
cp .env.example .env
# Edit .env — fill in API keys and MongoDB URI
```

> **MongoDB Atlas**: ensure your Atlas cluster's Network Access allows connections from your deployment IP (or `0.0.0.0/0` for cloud deployments with dynamic IPs).

---

## Run

```bash
# FastAPI server (MCP servers start in-process automatically):
uv run python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload --reload-dir SenkuNoChinou

# CLI app:
uv run python .\SenkuNoChinou\services\cli_app.py

# Docker:
docker-compose up --build

# Test individual MCP server:
uv run fastmcp dev inspector SenkuNoChinou/MCP/servers/<name>_server.py
```

Interactive API docs: `http://localhost:8000/docs`

---

## API

| Method | Path | Input | Output |
|--------|------|-------|--------|
| POST | `/senku/create-thread` | — | `{ thread_id }` |
| POST | `/senku/respond` | `{ query, thread_id }` | `{ response }` |
| POST | `/senku/respond-stream` | `{ query, thread_id }` | SSE token stream |
| POST | `/senku/transcribe` | multipart `audio` | `{ text }` |
| POST | `/senku/stt-respond` | multipart `audio`, form `thread_id` | `{ transcript, response }` |
| POST | `/senku/stt-respond-stream` | multipart `audio`, form `thread_id` | SSE transcript + token stream |

SSE stream format:
```
data: {"transcript": "..."}   ← STT endpoints only
data: {"token": "..."}        ← repeated
...
data: [DONE]
```

---

## Stack

Python 3.12 · uv · FastAPI · uvicorn · LangGraph · LangChain · LangSmith · FastMCP · langchain-mcp-adapters · ChatGroq · Groq Whisper API · pymongo · Beanie · MongoDB Atlas · Tavily · Jina · ntfy.sh · ytmusicapi · PlatformIO · ESP32
