import asyncio
import os
from typing import Literal

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from pydantic import BaseModel

load_dotenv()


class YonVerdict(BaseModel):
    fulfilled: bool
    target_gear: Literal["ichi", "ni", "san", "go"] = "ichi"


_YON_VERDICT_PROMPT = """You are Senku's quality verifier. Review the conversation and determine if the user's request was fully completed.

FULFILLED if:
- All requested actions were performed (tools returned success, not errors)
- The response directly addresses what the user asked
- No pending steps remain

NOT FULFILLED if:
- Tools returned errors or "not found"
- The agent responded vaguely without calling any tools
- The task was only partially done

If not fulfilled, set target_gear:
- ichi: research tasks (search, wiki, browse)
- ni: todos, calendar events, journal entries, productivity
- san: music, weather, datetime
- go: push notifications"""


_YON_RESPONSE_PROMPT = """You are Senku's response formatter. Write the final display response based on the conversation.

Rules:
- Max 2-3 paragraphs. Each paragraph max 4-5 lines.
- No greetings, no filler, no sign-offs.
- No emoji characters. Text emoticons only if it fits: :), :(, :D, :/, (o_o), <3.
- Do NOT echo or repeat raw tool output or system tags like "[Tool result]".
- Do NOT over-summarize — preserve key details, facts, and steps.
- Choose format based on content:
  * Instructions / recipes / how-to → numbered steps (Step 1: ... Step 2: ...)
  * Factual / explanatory → short dense paragraphs
  * Simple status / confirmation → one sentence
- If task failed: brief status of what happened."""


class GearYon:
    def __init__(self):
        llm = ChatGroq(
            model=os.getenv("YON_MODEL", "llama-3.3-70b-versatile"),
            api_key=os.environ["GROQ_API_KEY"],
        )
        self._verdict_llm = llm.with_structured_output(YonVerdict)
        self._response_llm = llm.with_config(tags=["yon_verifier"])

    async def verify(self, messages: list) -> tuple[YonVerdict, str]:
        context: list[tuple[str, str]] = []
        for m in messages[-8:]:
            if m.type == "human" and isinstance(m.content, str) and m.content.strip():
                context.append(("human", m.content))
            elif m.type == "ai" and isinstance(m.content, str) and m.content.strip():
                context.append(("assistant", m.content))
            elif m.type == "tool" and isinstance(m.content, str) and m.content.strip():
                context.append(("human", f"[Tool result]: {m.content}"))

        if not context:
            return YonVerdict(fulfilled=True, target_gear="ichi"), "Done."

        try:
            verdict, response = await asyncio.gather(
                self._verdict_llm.ainvoke([("system", _YON_VERDICT_PROMPT)] + context),
                self._response_llm.ainvoke([("system", _YON_RESPONSE_PROMPT)] + context),
            )
            return verdict, response.content
        except Exception:
            fallback = next(
                (m.content for m in reversed(messages) if isinstance(m.content, str) and m.content.strip()),
                "Done.",
            )
            return YonVerdict(fulfilled=True, target_gear="ichi"), fallback[:300]
