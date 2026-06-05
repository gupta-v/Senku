import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from dotenv import load_dotenv
load_dotenv()

from fastmcp import FastMCP
from SenkuNoChinou.MCP.tools.tavily_tool import internet_search
from SenkuNoChinou.MCP.tools.wiki_tool import ask_wikipedia
from SenkuNoChinou.MCP.tools.jina_tool import browse_url

mcp = FastMCP("ichi")

# ── Research ──────────────────────────────────────────────────────────────────
mcp.tool()(internet_search)
mcp.tool()(ask_wikipedia)
mcp.tool()(browse_url)


if __name__ == "__main__":
    mcp.run()
