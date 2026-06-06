import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq

from SenkuNoChinou.agents.gear_base import Gear
from SenkuNoChinou.MCP.prompts.go_prompt import get_go_system_prompt
from SenkuNoChinou.core.server import GO_URL

load_dotenv()

gear_go = Gear(
    name="go",
    servers={
        "go": {
            "url": GO_URL,
            "transport": "streamable_http",
        },
    },
    system_prompt=get_go_system_prompt(),
    tool_names={
        "get_datetime",
        "add_todo", "list_todos", "complete_todo", "edit_todo",
        "add_event", "list_events", "delete_event", "mark_event_status",
        "add_journal", "read_journal", "edit_journal",
    },
    llm=ChatGroq(
        model=os.getenv("GO_MODEL", os.getenv("ICHI_MODEL", "meta-llama/llama-4-scout-17b-16e-instruct")),
        api_key=os.environ["GROQ_API_KEY"],
    ),
)
