import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from dotenv import load_dotenv
load_dotenv()

from fastmcp import FastMCP
from SenkuNoChinou.MCP.prompts.san_prompt import get_san_system_prompt
from SenkuNoChinou.MCP.tools.music_tool import search_music
from SenkuNoChinou.MCP.tools.ntfy_tool import play_music_link
from SenkuNoChinou.MCP.tools.weather_tool import get_weather
from SenkuNoChinou.MCP.tools.datetime_tool import get_datetime
from SenkuNoChinou.MCP.tools.tavily_tool import internet_search
from SenkuNoChinou.MCP.tools.wiki_tool import ask_wikipedia

mcp = FastMCP("san")


@mcp.prompt()
def san_system() -> str:
    """Lifestyle/music/environment instructions for Gear San (三)."""
    return get_san_system_prompt()


# ── Music ─────────────────────────────────────────────────────────────────────
mcp.tool()(search_music)
mcp.tool()(play_music_link)

# ── Environment ───────────────────────────────────────────────────────────────
mcp.tool()(get_weather)
mcp.tool()(get_datetime)

# ── Research (context lookups) ────────────────────────────────────────────────
mcp.tool()(internet_search)
mcp.tool()(ask_wikipedia)


if __name__ == "__main__":
    mcp.run()
