import logging
from contextlib import asynccontextmanager

from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from SenkuNoChinou.models.agentState import AgentState
from SenkuNoChinou.agents.gear_ichi import gear_ichi
from SenkuNoChinou.agents.gear_ni import gear_ni
from SenkuNoChinou.agents.gear_san import gear_san
from SenkuNoChinou.agents.gear_router import GearRouter

log = logging.getLogger("senku.workflow")

_GEARS = [gear_ichi, gear_ni, gear_san]


async def respond(app, query: str, thread_id: str, callbacks: list | None = None) -> str:
    config: dict = {
        "configurable": {"thread_id": thread_id},
        "metadata": {"ls_thread_id": thread_id, "thread_id": thread_id},
    }
    if callbacks:
        config["callbacks"] = callbacks
    result = await app.ainvoke({"messages": [("human", query)]}, config=config)
    return result["messages"][-1].content


async def respond_stream(app, query: str, thread_id: str):
    config: dict = {
        "configurable": {"thread_id": thread_id},
        "metadata": {"ls_thread_id": thread_id, "thread_id": thread_id},
    }
    async for event in app.astream_events(
        {"messages": [("human", query)]}, config=config, version="v2"
    ):
        if event["event"] == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            if hasattr(chunk, "content") and chunk.content:
                yield chunk.content


@asynccontextmanager
async def build_workflow():
    """
    Boot all MCP servers, compile routed multi-gear LangGraph app, yield it.

    Usage:
        async with build_workflow() as app:
            result = await app.ainvoke(
                {"messages": [("human", "play something")]},
                config={"configurable": {"thread_id": "user-123"}},
            )
    """
    all_servers = {}
    for gear in _GEARS:
        all_servers.update(gear.servers)

    log.info("build_workflow starting — gears=%s", [g.name for g in _GEARS])
    client = MultiServerMCPClient(all_servers)
    tools  = await client.get_tools()
    log.info("MCP tools loaded count=%d names=%s", len(tools), [t.name for t in tools])
    agents = {g.name: await g.build_agent(tools, client) for g in _GEARS}
    log.info("agents built: %s", list(agents.keys()))
    router = GearRouter()

    # ── Nodes ──────────────────────────────────────────────────────────────────

    async def gear_router_node(state: AgentState) -> dict:
        gear = await router.classify(state["messages"])
        log.info("gear_router → %s", gear)
        return {"gear": gear}

    async def gear_ichi_node(state: AgentState) -> dict:
        log.info("gear_ichi invoked")
        result = await agents["ichi"].ainvoke({"messages": state["messages"]})
        log.info("gear_ichi done msg_count=%d", len(result["messages"]))
        return {"messages": result["messages"]}

    async def gear_ni_node(state: AgentState) -> dict:
        log.info("gear_ni invoked")
        result = await agents["ni"].ainvoke({"messages": state["messages"]})
        update: dict = {"messages": result["messages"]}
        for msg in result["messages"]:
            content = getattr(msg, "content", "")
            if isinstance(content, str) and "Playback started for video" in content:
                vid = content.split("video ")[-1].split(".")[0].strip()
                update["now_playing"] = {"video_id": vid, "title": "", "artist": ""}
                log.info("gear_ni now_playing video_id=%s", vid)
                break
        log.info("gear_ni done msg_count=%d", len(result["messages"]))
        return update

    async def gear_san_node(state: AgentState) -> dict:
        log.info("gear_san invoked")
        result = await agents["san"].ainvoke({"messages": state["messages"]})
        log.info("gear_san done msg_count=%d", len(result["messages"]))
        return {"messages": result["messages"]}

    # ── Graph ──────────────────────────────────────────────────────────────────

    graph = StateGraph(AgentState)

    graph.add_node("gear_router", gear_router_node)
    graph.add_node("gear_ichi",   gear_ichi_node)
    graph.add_node("gear_ni",     gear_ni_node)
    graph.add_node("gear_san",    gear_san_node)

    graph.add_edge(START, "gear_router")

    graph.add_conditional_edges(
        "gear_router",
        lambda state: state["gear"],
        {"ichi": "gear_ichi", "ni": "gear_ni", "san": "gear_san"},
    )

    graph.add_edge("gear_ichi", END)
    graph.add_edge("gear_ni",   END)
    graph.add_edge("gear_san",  END)

    app = graph.compile(checkpointer=MemorySaver())

    try:
        yield app
    finally:
        if hasattr(client, "aclose"):
            await client.aclose()
