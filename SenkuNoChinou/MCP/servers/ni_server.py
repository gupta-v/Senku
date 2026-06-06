import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from dotenv import load_dotenv
load_dotenv()

from fastmcp import FastMCP
from SenkuNoChinou.MCP.prompts.ni_prompt import get_ni_system_prompt
from SenkuNoChinou.MCP.tools.datetime_tool import get_datetime
from SenkuNoChinou.MCP.tools.todo_tool import add_todo, list_todos, complete_todo, edit_todo
from SenkuNoChinou.MCP.tools.calendar_tool import add_event, list_events, delete_event, mark_event_status
from SenkuNoChinou.MCP.tools.journal_tool import add_journal, read_journal, edit_journal

mcp = FastMCP("ni")


@mcp.prompt()
def ni_system() -> str:
    """Productivity instructions for Gear Ni (二)."""
    return get_ni_system_prompt()


# ── Datetime ──────────────────────────────────────────────────────────────────
mcp.tool()(get_datetime)

# ── Todo ──────────────────────────────────────────────────────────────────────
mcp.tool()(add_todo)
mcp.tool()(list_todos)
mcp.tool()(complete_todo)
mcp.tool()(edit_todo)

# ── Calendar ──────────────────────────────────────────────────────────────────
mcp.tool()(add_event)
mcp.tool()(list_events)
mcp.tool()(delete_event)
mcp.tool()(mark_event_status)

# ── Journal ───────────────────────────────────────────────────────────────────
mcp.tool()(add_journal)
mcp.tool()(read_journal)
mcp.tool()(edit_journal)


if __name__ == "__main__":
    mcp.run()
