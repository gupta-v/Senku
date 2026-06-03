import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq

from SenkuNoChinou.agents.gear_base import Gear

load_dotenv()

gear_san = Gear(
    name="san",
    servers={
        "san-prompts": {
            "command": "uv",
            "args": ["run", "fastmcp", "run", "SenkuNoChinou/MCP/servers/san_server.py"],
            "transport": "stdio",
        },
        "notify": {
            "command": "uv",
            "args": ["run", "fastmcp", "run", "SenkuNoChinou/MCP/servers/ntfy_server.py"],
            "transport": "stdio",
        },
    },
    prompt_server="san-prompts",
    prompt_name="san_system",
    tool_names={"send_notification"},
    llm=ChatGroq(
        model=os.getenv("SAN_MODEL", os.getenv("ICHI_MODEL", "llama-3.3-70b-versatile")),
        api_key=os.environ["GROQ_API_KEY"],
    ),
)
