import asyncio
import os
from typing import Literal

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from pydantic import BaseModel

load_dotenv()


class GoVerdict(BaseModel):
    fulfilled: bool
    target_gear: Literal["ichi", "ni", "san", "yon"] = "ichi"


_GO_VERDICT_PROMPT = """You are Senku's quality verifier. Review the conversation and determine if the user's request was fully completed.

FULFILLED if:
- The PRIMARY requested action succeeded (e.g. notification sent, music queued, todo added, search results returned)
- Ignore secondary/cleanup tool calls that failed AFTER the main action succeeded
- The response directly addresses what the user asked

NOT FULFILLED if:
- The primary action tool was never called
- The primary action tool returned an error or "not found"
- The agent responded vaguely without calling any tools

If not fulfilled, set target_gear:
- ichi: research tasks (search, wiki, browse)
- ni: todos, calendar events, journal entries, productivity
- san: music, weather, datetime
- yon: push notifications"""


_GO_RESPONSE_PROMPT = """Your PRIMARY job: write a clear, complete response to the user based on everything that happened in the conversation.
Verification is secondary — the response always comes first.

Rules:
- Max 2-3 paragraphs. Each paragraph max 4-5 lines.
- No greetings, no filler, no sign-offs.
- No emoji characters. Text emoticons only if it fits: :), :(, :D, :/, (o_o), <3.
- Do NOT echo raw system tags like "[Tool result]". DO include the key info from tool results.
- Do NOT over-summarize — preserve key details, facts, and steps.
- NEVER output just "Done.", "Ok.", "Sure.", "Sent.", or any single-word/single-phrase reply.
  Every response must describe WHAT was done with specifics.
- NEVER add meta-commentary about your own limitations: no "I don't have real-time info", no "I assumed the date", no "you can update this later", no "please note that". Report facts from tool results only.
- Do NOT suggest follow-up actions or offer to change things unless a tool explicitly returned an error.
- Choose format based on content:
  * Instructions / recipes / how-to → numbered steps (Step 1: ... Step 2: ...)
  * Factual / explanatory → short dense paragraphs
  * Simple status / confirmation → one full sentence with specifics
- Action confirmations (todo added/completed/edited, event saved/updated, journal logged, music sent, notification sent):
  Always state WHAT was done with the specific item name/title/date/priority.
  Example: "Added 'Buy groceries' due 2026-06-10 with high priority. Notification sent to your phone."
  Example: "Marked 'Fix bug' as done."
  Example: "Logged journal entry on the topic of burnout."
- If a tool returned "already marked as done": say "'[task]' was already marked as done."
- If ANY tool result starts with ⚠️, ❌, or ℹ️: the task FAILED or was blocked. Do NOT describe the action as completed. Relay the exact error to the user. This overrides all other rules.
- If task failed: relay the exact error, nothing more."""


class GearGo:
    def __init__(self):
        llm = ChatGroq(
            model=os.getenv("GO_MODEL", "llama-3.3-70b-versatile"),
            api_key=os.environ["GROQ_API_KEY"],
        )
        self._verdict_llm = llm.with_structured_output(GoVerdict)
        self._response_llm = llm.with_config(tags=["go_verifier"])

    @staticmethod
    def _content_str(content) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, str):
                    parts.append(block)
                elif isinstance(block, dict):
                    parts.append(block.get("text", str(block)))
            return " ".join(parts)
        return str(content) if content else ""

    async def verify(self, messages: list) -> tuple[GoVerdict, str]:
        _SKIP_CONTAINS = ("Push a notification to my phone for the action above",)
        context: list[tuple[str, str]] = []
        for m in messages[-12:]:
            text = self._content_str(m.content).strip()
            if not text:
                continue
            if m.type == "human":
                if any(s in text for s in _SKIP_CONTAINS):
                    continue
                context.append(("human", text))
            elif m.type == "ai":
                # Treat gear error returns as tool failures so response_llm applies the failure rule.
                if text.startswith("⚠️") or text.startswith("❌"):
                    context.append(("human", f"[Tool result]: {text}"))
                else:
                    context.append(("assistant", text))
            elif m.type == "tool":
                context.append(("human", f"[Tool result]: {text}"))

        if not context:
            return GoVerdict(fulfilled=True, target_gear="ichi"), "Done."

        tool_results = [c[1].removeprefix("[Tool result]: ") for c in context if c[0] == "human" and c[1].startswith("[Tool result]:")]

        try:
            verdict = await self._verdict_llm.ainvoke([("system", _GO_VERDICT_PROMPT)] + context)
        except Exception:
            verdict = GoVerdict(fulfilled=True, target_gear="ichi")

        try:
            response = await self._response_llm.ainvoke([("system", _GO_RESPONSE_PROMPT)] + context)
            text = response.content.strip()
            _bare = text.lower().rstrip("!. ")
            if not text or _bare in ("done", "ok", "sure", "sent", "noted", "got it"):
                text = tool_results[-1][:300] if tool_results else text or "Done."
        except Exception:
            text = tool_results[-1][:300] if tool_results else "Unable to generate response."

        return verdict, text
