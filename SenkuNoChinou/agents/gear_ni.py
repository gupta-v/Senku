import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq

from SenkuNoChinou.agents.gear_base import Gear
from SenkuNoChinou.MCP.prompts.ni_prompt import get_ni_system_prompt
from SenkuNoChinou.core.server import NI_URL

load_dotenv()

gear_ni = Gear(
    name="ni",
    servers={
        "ni": {
            "url": NI_URL,
            "transport": "streamable_http",
        },
    },
    system_prompt=get_ni_system_prompt(),
    tool_names={
        "get_datetime",
        "add_todo", "list_todos", "complete_todo", "edit_todo",
        "add_event", "list_events", "delete_event", "mark_event_status",
        "add_journal", "read_journal", "edit_journal",
    },
    llm=ChatGroq(
        model=os.getenv("NI_MODEL", "llama-3.3-70b-versatile"),
        api_key=os.environ["GROQ_API_KEY"],
        model_kwargs={"parallel_tool_calls": False},
    ),
)
