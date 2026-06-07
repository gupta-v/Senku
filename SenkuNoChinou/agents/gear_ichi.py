import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq

from SenkuNoChinou.agents.gear_base import Gear
from SenkuNoChinou.MCP.prompts.ichi_prompt import get_ichi_system_prompt
from SenkuNoChinou.core.server import ICHI_URL

load_dotenv()

gear_ichi = Gear(
    name="ichi",
    servers={
        "ichi": {
            "url": ICHI_URL,
            "transport": "streamable_http",
        },
    },
    system_prompt=get_ichi_system_prompt(),
    tool_names={"internet_search", "ask_wikipedia", "browse_url"},
    llm=ChatGroq(
        model=os.getenv("ICHI_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct"),
        api_key=os.environ["GROQ_API_KEY"],
        model_kwargs={"parallel_tool_calls": False},
    ),
)
