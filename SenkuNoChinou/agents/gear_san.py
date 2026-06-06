import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq

from SenkuNoChinou.agents.gear_base import Gear
from SenkuNoChinou.MCP.prompts.san_prompt import get_san_system_prompt
from SenkuNoChinou.core.server import SAN_URL

load_dotenv()

gear_san = Gear(
    name="san",
    servers={
        "san": {
            "url": SAN_URL,
            "transport": "streamable_http",
        },
    },
    system_prompt=get_san_system_prompt(),
    tool_names={"send_notification"},
    llm=ChatGroq(
        model=os.getenv("SAN_MODEL", "llama-3.1-8b-instant"),
        api_key=os.environ["GROQ_API_KEY"],
    ),
)
