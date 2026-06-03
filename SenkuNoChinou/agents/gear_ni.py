import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq

from SenkuNoChinou.agents.gear_base import Gear

load_dotenv()

gear_ni = Gear(
    name="ni",
    servers={
        "ni-prompts": {
            "command": "uv",
            "args": ["run", "fastmcp", "run", "SenkuNoChinou/MCP/servers/ni_server.py"],
            "transport": "stdio",
        },
        "environment": {
            "command": "uv",
            "args": ["run", "fastmcp", "run", "SenkuNoChinou/MCP/servers/environment_server.py"],
            "transport": "stdio",
        },
        "music": {
            "command": "uv",
            "args": ["run", "fastmcp", "run", "SenkuNoChinou/MCP/servers/music_server.py"],
            "transport": "stdio",
        },
        "ntfy": {
            "command": "uv",
            "args": ["run", "fastmcp", "run", "SenkuNoChinou/MCP/servers/ntfy_server.py"],
            "transport": "stdio",
        },
    },
    prompt_server="ni-prompts",
    prompt_name="ni_system",
    tool_names={
        "search_music",
        "play_music_link",
        "get_datetime",
        "get_weather",
    },
    llm=ChatGroq(
        model=os.getenv("NI_MODEL", "llama3-groq-70b-8192-tool-use-preview"),
        api_key=os.environ["GROQ_API_KEY"],
    ),
)
