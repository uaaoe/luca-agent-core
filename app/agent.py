"""
SentinelGraph Agent Architecture:
Supervisor Orchestration + Deterministic Policy Guard + Human-In-The-Loop (HITL) Interruption.
All state is persistently checkpointed via SQLite.
"""
import json
from typing import Annotated, Any, Dict, List, Literal, Optional, Sequence, TypedDict
import aiosqlite
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import Command, interrupt

from app.config import settings
from app.policy import PolicyEngine, PolicyStatus
from app.tools import tools, tools_by_name

# ---------------------------------------------------------------------------
# 1. LLM Initialization (Gemini 3.5 Flash Lite)
# ---------------------------------------------------------------------------
llm = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash-lite",
    google_api_key=settings.google_api_key,
    max_retries=2,
    request_timeout=15.0,
)

llm_with_tools = llm.bind_tools(tools)

# ---------------------------------------------------------------------------
# 2. Agent Typed State
# ---------------------------------------------------------------------------
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    supervisor: Optional[Dict[str, Any]]
    policy_audit: Optional[Dict[str, Any]]

# ---------------------------------------------------------------------------
# 3. Graph Nodes
# ---------------------------------------------------------------------------
async def supervisor_node(state: AgentState):
    """
    Supervisor Node: Classifies intent, assigns risk rating, and orchestrates.
    """
    last_msg = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            last_msg = str(msg.content)
            break

    last_lower = last_msg.lower()

    # Fast deterministic intent & risk classification
    if any(w in last_lower for w in ["transfer", "disbursement", "disburse", "pay", "wire", "fund"]):
        intent = "emergency_financial_allocation"
        risk_level = "CRITICAL"
        summary = "Financial resource allocation requested. Strict policy audit and operator authorization enforced."
    elif any(w in last_lower for w in ["scale", "replica", "rebalance", "pod", "capacity"]):
        intent = "service_scaling_rebalance"
        risk_level = "GUARDED"
        summary = "Operational infrastructure adjustment requested. Parameter bounds verification enforced."
    elif any(w in last_lower for w in ["telemetry", "metric", "cpu", "memory", "health", "status", "weather"]):
        intent = "diagnostic_telemetry_query"
        risk_level = "SAFE"
        summary = "Read-only diagnostic query. Immediate autonomous execution cleared."
    else:
        intent = "general_query"
        risk_level = "SAFE"
        summary = "General conversational task."

    return {
        "supervisor": {
            "intent": intent,
            "risk_level": risk_level,
            "summary": summary,
        }
    }


async def worker_node(state: AgentState):
    """
    Worker Node: Reasons with tools bound to Gemini.
    """
    system_instruction = (
        "You are SentinelGraph Worker, operating inside a strict simulated sandbox demo.\n"
        "Available tools:\n"
        "- query_cluster_telemetry: SAFE read-only metrics.\n"
        "- adjust_service_scaling: GUARDED service pod scaling.\n"
        "- simulate_emergency_disbursement: CRITICAL emergency fund allocation (strictly simulated demo sandbox).\n"
        "- get_weather_forecast, calculate_metric: SAFE utilities.\n"
        "Formulate precise tool calls when user requests actions. If a tool call is denied by the operator, "
        "politely acknowledge the rejection and summarize the policy rationale."
    )

    messages = [SystemMessage(content=system_instruction)] + list(state["messages"])
    response = await llm_with_tools.ainvoke(messages)
    return {"messages": [response]}


async def policy_guard_node(state: AgentState):
    """
    Deterministic Policy Guard Node:
    Intercepts tool calls, enforces assertion checks, and triggers HITL interrupts for CRITICAL actions.
    """
    last_message = state["messages"][-1]
    tool_messages = []
    audits = []

    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        for tc in last_message.tool_calls:
            policy = PolicyEngine.evaluate(tc["name"], tc["args"])
            audits.append({
                "tool": tc["name"],
                "status": policy.status.value,
                "risk_level": policy.risk_level.value,
                "reason": policy.reason,
            })

            # Case A: Outright blocked by policy (e.g. exceeded hard policy cap)
            if policy.status == PolicyStatus.BLOCKED:
                tool_messages.append(
                    ToolMessage(
                        content=f"[POLICY BLOCKED] {policy.reason}",
                        name=tc["name"],
                        tool_call_id=tc["id"],
                    )
                )

            # Case B: Requires Human-In-The-Loop authorization
            elif policy.requires_approval:
                decision = interrupt({
                    "tool": tc["name"],
                    "args": policy.sanitized_args,
                    "risk_level": policy.risk_level.value,
                    "reason": policy.reason,
                    "simulation_banner": policy.simulation_banner,
                })

                # Upon resumption with Command(resume=...):
                if not decision or not decision.get("approved", False):
                    feedback = decision.get("feedback", "Action denied by operator.") if isinstance(decision, dict) else "Action denied."
                    tool_messages.append(
                        ToolMessage(
                            content=f"[REJECTED BY OPERATOR] {feedback}",
                            name=tc["name"],
                            tool_call_id=tc["id"],
                        )
                    )

    return {
        "messages": tool_messages,
        "policy_audit": {"audits": audits},
    }


async def execute_tools_node(state: AgentState):
    """
    Execute Tools Node: Executes approved or safe simulated tools.
    """
    existing_tool_ids = {
        m.tool_call_id for m in state["messages"] if isinstance(m, ToolMessage)
    }
    
    last_ai = [
        m for m in state["messages"] if isinstance(m, AIMessage) and m.tool_calls
    ][-1]
    
    tool_messages = []
    for tc in last_ai.tool_calls:
        if tc["id"] not in existing_tool_ids:
            tool_name = tc["name"]
            tool_args = tc["args"]
            tool_id = tc["id"]

            if tool_name in tools_by_name:
                tool_func = tools_by_name[tool_name]
                output = await tool_func.ainvoke(tool_args)
            else:
                output = f"Error: Tool '{tool_name}' not found."

            tool_messages.append(
                ToolMessage(
                    content=str(output),
                    name=tool_name,
                    tool_call_id=tool_id,
                )
            )

    return {"messages": tool_messages}


# ---------------------------------------------------------------------------
# 4. Conditional Edge Routing
# ---------------------------------------------------------------------------
def should_continue_after_worker(state: AgentState) -> Literal["policy_guard", "__end__"]:
    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage) and bool(getattr(last_message, "tool_calls", None)):
        return "policy_guard"
    return "__end__"


def should_continue_after_guard(state: AgentState) -> Literal["execute_tools", "worker"]:
    """
    If all tool calls were already handled in policy_guard (e.g. blocked or rejected),
    route directly back to worker to formulate user-facing summary.
    Otherwise, proceed to execute remaining approved tools.
    """
    existing_tool_ids = {
        m.tool_call_id for m in state["messages"] if isinstance(m, ToolMessage)
    }
    last_ai = [
        m for m in state["messages"] if isinstance(m, AIMessage) and m.tool_calls
    ][-1]

    all_handled = all(tc["id"] in existing_tool_ids for tc in last_ai.tool_calls)
    if all_handled:
        return "worker"
    return "execute_tools"


# ---------------------------------------------------------------------------
# 5. Assemble Workflow
# ---------------------------------------------------------------------------
workflow = StateGraph(AgentState)  # type: ignore[bad-specialization]

workflow.add_node("supervisor", supervisor_node)
workflow.add_node("worker", worker_node)
workflow.add_node("policy_guard", policy_guard_node)
workflow.add_node("execute_tools", execute_tools_node)

workflow.add_edge(START, "supervisor")
workflow.add_edge("supervisor", "worker")
workflow.add_conditional_edges(
    "worker",
    should_continue_after_worker,
    {"policy_guard": "policy_guard", END: END},
)
workflow.add_conditional_edges(
    "policy_guard",
    should_continue_after_guard,
    {"execute_tools": "execute_tools", "worker": "worker"},
)
workflow.add_edge("execute_tools", "worker")

# ---------------------------------------------------------------------------
# 6. SQLite Checkpointer Lifecycle Management
# ---------------------------------------------------------------------------
_db_conn: Optional[aiosqlite.Connection] = None
_checkpointer: Optional[AsyncSqliteSaver] = None
_compiled_app = None

async def get_compiled_app():
    """Lazily initializes SQLite connection and compiles graph."""
    global _db_conn, _checkpointer, _compiled_app
    if _compiled_app is None:
        _db_conn = await aiosqlite.connect(settings.checkpoints_db_path)
        _checkpointer = AsyncSqliteSaver(_db_conn)
        await _checkpointer.setup()
        _compiled_app = workflow.compile(checkpointer=_checkpointer)
    return _compiled_app


def extract_clean_text(content) -> str:
    """Extract clean string text without Google signature/extras metadata."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict):
                if part.get("type") == "text" or "text" in part:
                    parts.append(part.get("text", ""))
            elif hasattr(part, "text"):
                parts.append(part.text)
            else:
                parts.append(str(part))
        return "".join(parts).strip()
    return str(content).strip()


# ---------------------------------------------------------------------------
# 7. Real-Time SSE Streaming Runners
# ---------------------------------------------------------------------------
async def stream_agent_execution(user_query: str, thread_id: str = "default-session"):
    """
    Executes a new user query, streaming real-time events.
    Pauses and yields 'hitl_required' if an interrupt is encountered.
    """
    app = await get_compiled_app()
    config = {"configurable": {"thread_id": thread_id}}
    input_payload = {"messages": [HumanMessage(content=user_query)]}

    async for event in app.astream(input_payload, config=config, stream_mode="updates"):
        # Handle Interrupts
        if "__interrupt__" in event:
            interrupts = event["__interrupt__"]
            for intr in interrupts:
                val = intr.value if hasattr(intr, "value") else intr
                yield json.dumps({
                    "type": "hitl_required",
                    "thread_id": thread_id,
                    **(val if isinstance(val, dict) else {"details": str(val)}),
                })
            return

        # Handle Node Updates
        for node_name, state_update in event.items():
            if node_name == "supervisor" and "supervisor" in state_update:
                sup = state_update["supervisor"]
                yield json.dumps({
                    "type": "supervisor",
                    "intent": sup.get("intent"),
                    "risk_level": sup.get("risk_level"),
                    "summary": sup.get("summary"),
                })

            elif node_name == "policy_guard" and "policy_audit" in state_update:
                for audit in state_update["policy_audit"].get("audits", []):
                    yield json.dumps({
                        "type": "policy_check",
                        **audit,
                    })

            messages = state_update.get("messages", [])
            for msg in messages:
                if isinstance(msg, AIMessage) and msg.tool_calls:
                    for call in msg.tool_calls:
                        yield json.dumps({
                            "type": "tool_call",
                            "tool": call["name"],
                            "args": call["args"],
                        })

                elif isinstance(msg, ToolMessage):
                    yield json.dumps({
                        "type": "tool_result",
                        "tool": msg.name,
                        "output": msg.content,
                    })

                elif isinstance(msg, AIMessage):
                    clean_text = extract_clean_text(msg.content)
                    if clean_text:
                        yield json.dumps({
                            "type": "message",
                            "content": clean_text,
                        })


async def resume_agent_execution(thread_id: str, approved: bool, feedback: str = ""):
    """
    Resumes an interrupted graph execution using LangGraph Command(resume=...).
    """
    app = await get_compiled_app()
    config = {"configurable": {"thread_id": thread_id}}
    resume_payload = Command(resume={"approved": approved, "feedback": feedback})

    async for event in app.astream(resume_payload, config=config, stream_mode="updates"):
        if "__interrupt__" in event:
            interrupts = event["__interrupt__"]
            for intr in interrupts:
                val = intr.value if hasattr(intr, "value") else intr
                yield json.dumps({
                    "type": "hitl_required",
                    "thread_id": thread_id,
                    **(val if isinstance(val, dict) else {"details": str(val)}),
                })
            return

        for node_name, state_update in event.items():
            if node_name == "policy_guard" and "policy_audit" in state_update:
                for audit in state_update["policy_audit"].get("audits", []):
                    yield json.dumps({
                        "type": "policy_check",
                        **audit,
                    })

            messages = state_update.get("messages", [])
            for msg in messages:
                if isinstance(msg, AIMessage) and msg.tool_calls:
                    for call in msg.tool_calls:
                        yield json.dumps({
                            "type": "tool_call",
                            "tool": call["name"],
                            "args": call["args"],
                        })

                elif isinstance(msg, ToolMessage):
                    yield json.dumps({
                        "type": "tool_result",
                        "tool": msg.name,
                        "output": msg.content,
                    })

                elif isinstance(msg, AIMessage):
                    clean_text = extract_clean_text(msg.content)
                    if clean_text:
                        yield json.dumps({
                            "type": "message",
                            "content": clean_text,
                        })


async def get_thread_state_info(thread_id: str) -> Dict[str, Any]:
    """Inspects the thread's checkpoint state and returns any pending interrupts."""
    app = await get_compiled_app()
    config = {"configurable": {"thread_id": thread_id}}
    state = await app.aget_state(config)
    
    pending = []
    if state and state.tasks:
        for task in state.tasks:
            for intr in getattr(task, "interrupts", []):
                pending.append(intr.value if hasattr(intr, "value") else str(intr))

    return {
        "thread_id": thread_id,
        "next_nodes": list(state.next) if state else [],
        "has_pending_interrupt": len(pending) > 0,
        "pending_interrupts": pending,
    }
