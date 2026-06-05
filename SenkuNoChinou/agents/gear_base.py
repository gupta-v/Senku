from dataclasses import dataclass, field
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent


@dataclass
class Gear:
    name: str
    servers: dict
    tool_names: set[str]
    llm: object
    # Set system_prompt directly to skip the MCP prompt subprocess entirely.
    # If None, gear has no system prompt.
    system_prompt: str | None = field(default=None)
    # Legacy: MCP prompt server/name — only used if system_prompt is None.
    prompt_server: str = field(default="")
    prompt_name: str = field(default="")

    async def build_agent(self, all_tools: list, client: MultiServerMCPClient):
        """Build a ReAct agent with only this gear's designated tools."""
        # Filter the shared pool down to this gear's tools only.
        # Each agent sees a small, focused tool set — avoids bloated prompts.
        if self.tool_names:
            tools = [t for t in all_tools if t.name in self.tool_names]
        else:
            tools = []  # gear with no tools (e.g. gear_yon — pure LLM)

        prompt = self.system_prompt

        if prompt is None and self.prompt_server:
            try:
                messages = await client.get_prompt(self.prompt_server, self.prompt_name)
                prompt = messages[0].content if messages else None
            except Exception:
                pass

        kwargs = {"prompt": prompt} if prompt else {}
        return create_react_agent(self.llm, tools, **kwargs)

