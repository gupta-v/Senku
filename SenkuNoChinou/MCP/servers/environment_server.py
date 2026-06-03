import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from dotenv import load_dotenv
load_dotenv()

from fastmcp import FastMCP
from SenkuNoChinou.MCP.tools.datetime_tool import get_datetime
from SenkuNoChinou.MCP.tools.weather_tool import get_weather

mcp = FastMCP("environment")
mcp.tool()(get_datetime)
mcp.tool()(get_weather)

if __name__ == "__main__":
    mcp.run()
