import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from dotenv import load_dotenv
load_dotenv()

from fastmcp import FastMCP
from SenkuNoChinou.MCP.tools.tavily_tool import internet_search

mcp = FastMCP("tavily")
mcp.tool()(internet_search)

if __name__ == "__main__":
    mcp.run()
