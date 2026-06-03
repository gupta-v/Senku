import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from dotenv import load_dotenv
load_dotenv()

from fastmcp import FastMCP
from SenkuNoChinou.MCP.prompts.san_prompt import get_san_system_prompt

mcp = FastMCP("san-prompts")


@mcp.prompt()
def san_system() -> str:
    """Action/notification instructions for Gear San (三)."""
    return get_san_system_prompt()


if __name__ == "__main__":
    mcp.run()
