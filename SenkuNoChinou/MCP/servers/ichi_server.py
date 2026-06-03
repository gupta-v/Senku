import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from dotenv import load_dotenv
load_dotenv()

from fastmcp import FastMCP
from SenkuNoChinou.MCP.prompts.ichi_prompt import get_ichi_system_prompt

mcp = FastMCP("prompts")


@mcp.prompt()
def ichi_system() -> str:
    """Core identity and operating instructions for Senku (千空の知能)."""
    return get_ichi_system_prompt()


if __name__ == "__main__":
    mcp.run()
