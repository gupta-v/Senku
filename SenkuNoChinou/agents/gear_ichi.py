import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq

from SenkuNoChinou.agents.gear_base import Gear

load_dotenv()

gear_ichi = Gear(
    name="ichi",
    servers={
        "ichi-prompts": {
            "command": "uv",
            "args": ["run", "fastmcp", "run", "SenkuNoChinou/MCP/servers/ichi_server.py"],
            "transport": "stdio",
        },
        "wikipedia": {
            "command": "uv",
            "args": ["run", "fastmcp", "run", "SenkuNoChinou/MCP/servers/wikipedia_server.py"],
            "transport": "stdio",
        },
        "search": {
            "command": "uv",
            "args": ["run", "fastmcp", "run", "SenkuNoChinou/MCP/servers/tavily_server.py"],
            "transport": "stdio",
        },
        "browse": {
            "command": "uv",
            "args": ["run", "fastmcp", "run", "SenkuNoChinou/MCP/servers/jina_server.py"],
            "transport": "stdio",
        },
    },
    prompt_server="ichi-prompts",
    prompt_name="ichi_system",
    tool_names={"ask_wikipedia", "internet_search", "browse_url"},
    llm=ChatGroq(
        model=os.getenv("ICHI_MODEL", "llama-3.3-70b-versatile"),
        api_key=os.environ["GROQ_API_KEY"],
    ),
)
