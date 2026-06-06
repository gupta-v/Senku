import os
from typing import Literal

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from pydantic import BaseModel

load_dotenv()


class RouteDecision(BaseModel):
    gear: Literal["ichi", "ni", "san", "go"]


_ROUTER_PROMPT = """Classify the conversation and return the correct gear name. One word only.

- ichi: research, web search, wikipedia, browse URLs, news, general knowledge, factual questions, follow-up questions on any topic
- ni: todos, tasks, work items, calendar events, scheduling, journal entries, productivity — anything involving adding/listing/completing/editing tasks or events, or logging what happened
- san: music (play/search/skip), weather, time, date
- go: send push notification to phone ONLY when user explicitly says "notify me", "send notification", or "push alert"

When in doubt, return ichi."""


class GearZero:

    def __init__(self):
        llm = ChatGroq(
            model=os.getenv("ICHI_MODEL", "llama-3.3-70b-versatile"),
            api_key=os.environ["GROQ_API_KEY"],
        )
        self._llm = llm.with_structured_output(RouteDecision)

    async def classify(self, messages: list) -> str:
        # pass last 3 messages for context so follow-ups route correctly
        context = messages[-3:] if len(messages) >= 3 else messages
        try:
            decision: RouteDecision = await self._llm.ainvoke(
                [("system", _ROUTER_PROMPT)] + [(m.type, m.content) for m in context]
            )
            return decision.gear
        except Exception:
            return "ichi"  # safe default
