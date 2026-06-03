from dataclasses import dataclass
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent


@dataclass
class Gear:
    name: str
    servers: dict
    prompt_server: str
    prompt_name: str
    tool_names: set[str]
    llm: object

    async def build_agent(self, all_tools: list, client: MultiServerMCPClient):
        """Fetch prompt from MCP, filter tools, return compiled ReAct agent."""
        prompt = None
        try:
            messages = await client.get_prompt(self.prompt_server, self.prompt_name)
            prompt = messages[0].content if messages else None
        except Exception:
            pass

        my_tools = [t for t in all_tools if t.name in self.tool_names]
        kwargs = {"prompt": prompt} if prompt else {}
        return create_react_agent(self.llm, my_tools, **kwargs)
