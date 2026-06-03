import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from dotenv import load_dotenv
load_dotenv()

from fastmcp import FastMCP
from SenkuNoChinou.MCP.tools.music_tool import search_music

mcp = FastMCP("music")
mcp.tool()(search_music)

if __name__ == "__main__":
    mcp.run()
