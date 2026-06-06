import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from dotenv import load_dotenv
load_dotenv()

from fastmcp import FastMCP
from SenkuNoChinou.MCP.prompts.go_prompt import get_go_system_prompt
from SenkuNoChinou.MCP.tools.ntfy_tool import send_notification

mcp = FastMCP("go")


@mcp.prompt()
def go_system() -> str:
    """Action/notification instructions for Gear Go (五)."""
    return get_go_system_prompt()


# ── Notifications ─────────────────────────────────────────────────────────────
mcp.tool()(send_notification)


if __name__ == "__main__":
    mcp.run()
