import os
from typing import Literal

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from pydantic import BaseModel

load_dotenv()


class RouteDecision(BaseModel):
    gear: Literal["ichi", "ni", "san"]


_ROUTER_PROMPT = """Classify the conversation and return the correct gear name. One word only.

- ichi: research, web search, wikipedia, browse URLs, news, general knowledge, follow-up questions on any topic
- ni: music (play/search/skip), weather, time, date
- san: send notification, push alert, notify me

When in doubt, return ichi."""


class GearRouter:

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
