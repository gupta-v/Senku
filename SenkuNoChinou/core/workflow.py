import asyncio
import logging
from contextlib import asynccontextmanager

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.messages import AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from SenkuNoChinou.models.agentState import AgentState
from SenkuNoChinou.agents.gear_ichi import gear_ichi
from SenkuNoChinou.agents.gear_ni import gear_ni
from SenkuNoChinou.agents.gear_san import gear_san
from SenkuNoChinou.agents.gear_go import gear_go
from SenkuNoChinou.agents.gear_yon import GearYon
from SenkuNoChinou.agents.gear_zero import GearZero

log = logging.getLogger("senku.workflow")

_GEARS = [gear_ichi, gear_ni, gear_san, gear_go]

_MAX_RETRIES = 2


async def respond(app, query: str, thread_id: str, callbacks: list | None = None) -> str:
    config: dict = {
        "configurable": {"thread_id": thread_id},
        "metadata": {"ls_thread_id": thread_id, "thread_id": thread_id},
    }
    if callbacks:
        config["callbacks"] = callbacks
    result = await app.ainvoke(
        {"messages": [("human", query)], "retry_count": 0, "fulfilled": False},
        config=config,
    )
    return result["messages"][-1].content


async def respond_stream(app, query: str, thread_id: str):
    config: dict = {
        "configurable": {"thread_id": thread_id},
        "metadata": {"ls_thread_id": thread_id, "thread_id": thread_id},
    }
    async for event in app.astream_events(
        {"messages": [("human", query)], "retry_count": 0, "fulfilled": False},
        config=config,
        version="v2",
    ):
        if event["event"] == "on_chat_model_stream":
            if "yon_verifier" in event.get("tags", []):
                chunk = event["data"]["chunk"]
                if hasattr(chunk, "content") and chunk.content:
                    yield chunk.content


@asynccontextmanager
async def build_workflow():
    all_servers = {}
    for gear in _GEARS:
        all_servers.update(gear.servers)

    log.info("build_workflow starting — gears=%s", [g.name for g in _GEARS])
    client = MultiServerMCPClient(all_servers)
    mcp_tools = await client.get_tools()
    log.info("tools ready mcp=%d", len(mcp_tools))

    built = await asyncio.gather(*[g.build_agent(mcp_tools, client) for g in _GEARS])
    agents = {g.name: agent for g, agent in zip(_GEARS, built)}
    log.info("agents built: %s", list(agents.keys()))

    router = GearZero()
    yon = GearYon()

    # ── Nodes ──────────────────────────────────────────────────────────────────

    async def gear_zero_node(state: AgentState) -> dict:
        gear = await router.classify(state["messages"])
        log.info("gear_zero → %s", gear)
        return {"gear": gear}

    async def _invoke_gear(name: str, state: AgentState) -> list:
        try:
            result = await agents[name].ainvoke({"messages": state["messages"]})
            log.info("gear_%s done msg_count=%d", name, len(result["messages"]))
            return result["messages"]
        except Exception as exc:
            log.exception("gear_%s failed: %s", name, exc)
            body = getattr(exc, "body", None)
            if isinstance(body, dict):
                failed_gen = body.get("error", {}).get("failed_generation")
                if failed_gen:
                    log.info("gear_%s recovering failed_generation len=%d", name, len(failed_gen))
                    return [AIMessage(content=failed_gen)]
            return [AIMessage(content="I wasn't able to complete that request. Please try again.")]

    async def gear_ichi_node(state: AgentState) -> dict:
        log.info("gear_ichi invoked")
        return {"messages": await _invoke_gear("ichi", state)}

    async def gear_ni_node(state: AgentState) -> dict:
        log.info("gear_ni invoked")
        return {"messages": await _invoke_gear("ni", state)}

    async def gear_san_node(state: AgentState) -> dict:
        log.info("gear_san invoked")
        return {"messages": await _invoke_gear("san", state)}

    async def gear_go_node(state: AgentState) -> dict:
        log.info("gear_go invoked")
        return {"messages": await _invoke_gear("go", state)}

    async def gear_yon_node(state: AgentState) -> dict:
        log.info("gear_yon verifying retry_count=%d", state.get("retry_count", 0))
        verdict, response_text = await yon.verify(state["messages"])
        log.info("gear_yon verdict fulfilled=%s target=%s", verdict.fulfilled, verdict.target_gear)

        new_retry = state.get("retry_count", 0) + (0 if verdict.fulfilled else 1)
        return {
            "messages": [AIMessage(content=response_text)],
            "fulfilled": verdict.fulfilled,
            "retry_count": new_retry,
            "gear": verdict.target_gear if not verdict.fulfilled else state.get("gear", "ichi"),
        }

    # ── Graph ──────────────────────────────────────────────────────────────────

    graph = StateGraph(AgentState)

    graph.add_node("gear_zero", gear_zero_node)
    graph.add_node("gear_ichi", gear_ichi_node)
    graph.add_node("gear_ni",   gear_ni_node)
    graph.add_node("gear_san",  gear_san_node)
    graph.add_node("gear_go",   gear_go_node)
    graph.add_node("gear_yon",  gear_yon_node)

    graph.add_edge(START, "gear_zero")

    graph.add_conditional_edges(
        "gear_zero",
        lambda state: state["gear"],
        {"ichi": "gear_ichi", "ni": "gear_ni", "san": "gear_san", "go": "gear_go"},
    )

    graph.add_edge("gear_ichi", "gear_yon")
    graph.add_edge("gear_ni",   "gear_yon")
    graph.add_edge("gear_san",  "gear_yon")
    graph.add_edge("gear_go",   "gear_yon")

    def _yon_route(state: AgentState) -> str:
        if state.get("fulfilled", True) or state.get("retry_count", 0) >= _MAX_RETRIES:
            return END
        return state["gear"]

    graph.add_conditional_edges(
        "gear_yon",
        _yon_route,
        {"ichi": "gear_ichi", "ni": "gear_ni", "san": "gear_san", "go": "gear_go", END: END},
    )

    app = graph.compile(checkpointer=MemorySaver())

    try:
        yield app
    finally:
        if hasattr(client, "aclose"):
            await client.aclose()
