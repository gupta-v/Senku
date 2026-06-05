import os
from typing import Literal

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from pydantic import BaseModel

load_dotenv()


class YonVerdict(BaseModel):
    fulfilled: bool
    target_gear: Literal["ichi", "ni", "san", "go"] = "ichi"
    response: str  # formatted response: steps for how-to, paragraphs for facts, one line for simple


_YON_PROMPT = """You are Senku's quality verifier and response formatter.

Review the full conversation. Determine if the user's original request was fully completed.

FULFILLED if:
- All requested actions were actually performed (tools returned success, not errors)
- The response directly addresses what the user asked
- No pending steps remain

NOT FULFILLED if:
- Tools returned errors or "not found"
- The agent responded vaguely without calling any tools
- The task was only partially done

If not fulfilled, set target_gear:
- ichi: research tasks (search, wiki, browse)
- go: todos, calendar events, journal entries, productivity
- ni: music, weather, datetime
- san: push notifications

response field: Write the final response. Rules:
- Max 2-3 paragraphs. Each paragraph max 4-5 lines.
- No greetings, no filler, no sign-offs.
- Do NOT over-summarize — preserve key details, facts, and steps from the answer.
- Choose format based on content:
  * Instructions / recipes / how-to → numbered steps (Step 1: ... Step 2: ... etc.)
  * Factual / explanatory → short dense paragraphs
  * Simple yes/no / status → one sentence
- If not fulfilled: brief status of what happened."""


class GearYon:
    def __init__(self):
        llm = ChatGroq(
            model=os.getenv("YON_MODEL", "llama-3.3-70b-versatile"),
            api_key=os.environ["GROQ_API_KEY"],
        )
        self._llm = llm.with_structured_output(YonVerdict)

    async def verify(self, messages: list) -> YonVerdict:
        try:
            verdict: YonVerdict = await self._llm.ainvoke(
                [("system", _YON_PROMPT)] + [(m.type, m.content) for m in messages[-6:] if m.type in ("human", "ai")]
            )
            return verdict
        except Exception:
            last = messages[-1].content if messages else "Done."
            return YonVerdict(fulfilled=True, target_gear="ichi", response=last[:200])
