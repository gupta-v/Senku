import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from SenkuNoChinou.models.agentState import AgentState
from SenkuNoChinou.agents.gear_ichi import gear_ichi
from SenkuNoChinou.agents.gear_ni import gear_ni
from SenkuNoChinou.agents.gear_san import gear_san
from SenkuNoChinou.agents.gear_yon import gear_yon
from SenkuNoChinou.agents.gear_go import GearGo, GoVerdict
from SenkuNoChinou.agents.gear_zero import GearZero

log = logging.getLogger("senku.workflow")

_GEARS = [gear_ichi, gear_ni, gear_san, gear_yon]

_MAX_RETRIES = 2

_NI_NOTIFY_TRIGGER = (
    "SEND_NOTIFICATION: Read the tool result above. "
    "Title = the exact item name (task name, event title, or journal title) from that result — "
    "never generic phrases like 'Action Above', 'Notification', 'Update', 'New Item'. "
    "Body = one sentence describing what was done."
)


async def respond(app, query: str, thread_id: str, callbacks: list | None = None) -> str:
    config: dict = {
        "configurable": {"thread_id": thread_id},
        "metadata": {"ls_thread_id": thread_id, "thread_id": thread_id},
    }
    if callbacks:
        config["callbacks"] = callbacks
    result = await app.ainvoke(
        {"messages": [("human", query)], "retry_count": 0, "fulfilled": False,
         "current_date": datetime.now(timezone.utc).strftime("%A, %Y-%m-%d %H:%M UTC")},
        config=config,
    )
    return result["messages"][-1].content


async def respond_stream(app, query: str, thread_id: str):
    config: dict = {
        "configurable": {"thread_id": thread_id},
        "metadata": {"ls_thread_id": thread_id, "thread_id": thread_id},
    }
    async for event in app.astream_events(
        {"messages": [("human", query)], "retry_count": 0, "fulfilled": False,
         "current_date": datetime.now(timezone.utc).strftime("%A, %Y-%m-%d %H:%M UTC")},
        config=config,
        version="v2",
    ):
        if event["event"] == "on_chat_model_stream":
            if "go_verifier" in event.get("tags", []):
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
    go = GearGo()

    # ── Nodes ──────────────────────────────────────────────────────────────────

    async def gear_zero_node(state: AgentState) -> dict:
        gear = await router.classify(state["messages"])
        log.info("gear_zero → %s", gear)
        return {"gear": gear}

    def _date_prefix(state: AgentState) -> list:
        d = state.get("current_date", "")
        return [SystemMessage(content=f"Current date and time: {d}")] if d else []

    async def _invoke_gear(name: str, state: AgentState, inject_date: bool = False) -> list:
        msgs = (_date_prefix(state) + list(state["messages"])) if inject_date else state["messages"]
        try:
            result = await agents[name].ainvoke({"messages": msgs})
            log.info("gear_%s done msg_count=%d", name, len(result["messages"]))
            return result["messages"]
        except Exception as exc:
            log.exception("gear_%s failed: %s", name, exc)
            body = getattr(exc, "body", None)
            if isinstance(body, dict):
                failed_gen = body.get("error", {}).get("failed_generation")
                if failed_gen:
                    log.info("gear_%s failed_generation len=%d — returning error for retry", name, len(failed_gen))
            return [AIMessage(content="⚠️ I wasn't able to complete that request due to a processing error. Please try again.")]

    async def gear_ichi_node(state: AgentState) -> dict:
        log.info("gear_ichi invoked")
        return {"messages": await _invoke_gear("ichi", state)}

    async def gear_ni_node(state: AgentState) -> dict:
        log.info("gear_ni invoked")
        messages = await _invoke_gear("ni", state, inject_date=True)
        # First pass only: inject notify trigger if the action succeeded (no tool error).
        if state.get("retry_count", 0) == 0:
            _err_markers = ("⚠️", "❌", "wasn't able to complete", "processing error")

            def _has_error_content(m) -> bool:
                c = m.content
                if isinstance(c, list):
                    c = " ".join(b.get("text", str(b)) if isinstance(b, dict) else str(b) for b in c)
                return isinstance(c, str) and any(marker in c for marker in _err_markers)

            has_error = any(_has_error_content(m) for m in messages)
            if not has_error:
                # Embed last tool result so gear_yon gets exact item name inline.
                last_tool_result = ""
                for m in reversed(messages):
                    if getattr(m, "type", None) == "tool":
                        c = m.content
                        if isinstance(c, list):
                            c = " ".join(b.get("text", str(b)) if isinstance(b, dict) else str(b) for b in c)
                        last_tool_result = str(c).strip()
                        break
                trigger = f"{last_tool_result}\n{_NI_NOTIFY_TRIGGER}" if last_tool_result else _NI_NOTIFY_TRIGGER
                messages.append(HumanMessage(content=trigger))
        return {"messages": messages}

    async def gear_san_node(state: AgentState) -> dict:
        log.info("gear_san invoked")
        return {"messages": await _invoke_gear("san", state, inject_date=True)}

    async def gear_yon_node(state: AgentState) -> dict:
        log.info("gear_yon invoked")
        # Pass ONLY the trigger message — prevents model from seeing ni tool calls
        # (delete_event, complete_todo, etc.) and trying to re-invoke them.
        msgs = state.get("messages", [])
        trigger = msgs[-1] if msgs and getattr(msgs[-1], "type", None) == "human" else None
        invoke_msgs = [trigger] if trigger else msgs
        try:
            result = await agents["yon"].ainvoke({"messages": invoke_msgs})
            log.info("gear_yon done msg_count=%d", len(result["messages"]))
            return {"messages": result["messages"]}
        except Exception as exc:
            log.exception("gear_yon failed: %s", exc)
            return {"messages": [AIMessage(content="⚠️ Notification could not be sent.")]}

    async def gear_go_node(state: AgentState) -> dict:
        log.info("gear_go verifying retry_count=%d", state.get("retry_count", 0))
        verdict, response_text = await go.verify(state["messages"])
        log.info("gear_go verdict fulfilled=%s target=%s", verdict.fulfilled, verdict.target_gear)

        # Notifications are fire-and-forget — never retry yon.
        # Detect by finding the trigger HumanMessage and any ToolMessage after it.
        msgs = state["messages"]
        trigger_idx = next(
            (i for i, m in enumerate(msgs)
             if getattr(m, "type", None) == "human"
             and _NI_NOTIFY_TRIGGER in (m.content if isinstance(m.content, str) else "")),
            None,
        )
        yon_fired = trigger_idx is not None and any(
            getattr(m, "type", None) == "tool" for m in msgs[trigger_idx:]
        )
        if yon_fired:
            verdict = GoVerdict(fulfilled=True, target_gear="ichi")

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
    graph.add_node("gear_yon",  gear_yon_node)
    graph.add_node("gear_go",   gear_go_node)

    graph.add_edge(START, "gear_zero")

    graph.add_conditional_edges(
        "gear_zero",
        lambda state: state["gear"],
        {"ichi": "gear_ichi", "ni": "gear_ni", "san": "gear_san", "yon": "gear_yon"},
    )

    graph.add_edge("gear_ichi", "gear_go")
    graph.add_edge("gear_san",  "gear_go")
    graph.add_edge("gear_yon",  "gear_go")

    # gear_ni: first pass with no error → gear_yon (auto-notify) → gear_go
    #          error or retry           → gear_go directly
    def _ni_route(state: AgentState) -> str:
        msgs = state.get("messages", [])
        if msgs:
            last = msgs[-1]
            if getattr(last, "type", None) == "human":
                c = last.content if isinstance(last.content, str) else ""
                if _NI_NOTIFY_TRIGGER in c:
                    return "gear_yon"
        return "gear_go"

    graph.add_conditional_edges(
        "gear_ni",
        _ni_route,
        {"gear_yon": "gear_yon", "gear_go": "gear_go"},
    )

    def _go_route(state: AgentState) -> str:
        if state.get("fulfilled", True) or state.get("retry_count", 0) >= _MAX_RETRIES:
            return END
        return state["gear"]

    graph.add_conditional_edges(
        "gear_go",
        _go_route,
        {"ichi": "gear_ichi", "ni": "gear_ni", "san": "gear_san", "yon": "gear_yon", END: END},
    )

    app = graph.compile(checkpointer=MemorySaver())

    try:
        yield app
    finally:
        if hasattr(client, "aclose"):
            await client.aclose()
