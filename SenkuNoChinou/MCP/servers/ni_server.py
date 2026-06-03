import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from dotenv import load_dotenv
load_dotenv()

from fastmcp import FastMCP
from SenkuNoChinou.MCP.prompts.ni_prompt import get_ni_system_prompt

mcp = FastMCP("ni-prompts")


@mcp.prompt()
def ni_system() -> str:
    """Lifestyle/music/environment instructions for Gear Ni (二)."""
    return get_ni_system_prompt()


if __name__ == "__main__":
    mcp.run()
