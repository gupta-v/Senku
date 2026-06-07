import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq

from SenkuNoChinou.agents.gear_base import Gear
from SenkuNoChinou.MCP.prompts.yon_prompt import get_yon_system_prompt
from SenkuNoChinou.core.server import GO_URL

load_dotenv()

gear_yon = Gear(
    name="yon",
    servers={
        "go": {
            "url": GO_URL,
            "transport": "streamable_http",
        },
    },
    system_prompt=get_yon_system_prompt(),
    tool_names={"send_notification"},
    llm=ChatGroq(
        model=os.getenv("YON_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct"),
        api_key=os.environ["GROQ_API_KEY"],
        model_kwargs={"parallel_tool_calls": False},
    ),
)
