import asyncio
import json
from typing import Annotated, Any, Literal, Sequence, TypedDict
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

from app.config import settings
from app.tools.registry import registry

# Discover all tools dynamically on startup
registry.auto_discover()

# ---------------------------------------------------------------------------
# 1. Gemini LLM Initialization
# ---------------------------------------------------------------------------
llm = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash-lite",
    google_api_key=settings.google_api_key,
    max_retries=2,
    request_timeout=15.0,
)


def resolve_model(active_tools: Sequence[str] | None = None):
    """
    Bind tools to LLM if requested, otherwise return the raw LLM.
    Ensures zero tools are bound by default (strict opt-in).
    """
    if active_tools:
        selected_tools = registry.get_tools(active_tools)
        if selected_tools:
            return llm.bind_tools(selected_tools)
    return llm


# ---------------------------------------------------------------------------
# 2. Agent State & Nodes
# ---------------------------------------------------------------------------
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


async def call_model(state: AgentState, config: RunnableConfig | None = None):
    """Invoke Gemini with dynamic tool binding from RunnableConfig."""
    active_tools: list[str] = []
    if config and "configurable" in config:
        active_tools = config["configurable"].get("active_tools") or []

    model = resolve_model(active_tools)
    response = await model.ainvoke(state["messages"])
    return {"messages": [response]}


async def execute_tools(state: AgentState):
    """Execute tools requested by Gemini concurrently with resilient error handling."""
    last_message = state["messages"][-1]
    tool_messages: list[ToolMessage] = []

    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        async def run_single_tool(call: dict[str, Any]) -> ToolMessage:
            tool_name = call["name"]
            tool_args = call.get("args", {})
            tool_id = call.get("id")

            selected_tool = registry.get_tool(tool_name)
            if not selected_tool:
                return ToolMessage(
                    content=f"Error: Tool '{tool_name}' not found.",
                    name=tool_name,
                    tool_call_id=tool_id,
                )

            try:
                tool_output = await selected_tool.ainvoke(tool_args)
                return ToolMessage(
                    content=str(tool_output),
                    name=tool_name,
                    tool_call_id=tool_id,
                )
            except Exception as exc:
                return ToolMessage(
                    content=f"Tool execution error: {str(exc)}",
                    name=tool_name,
                    tool_call_id=tool_id,
                )

        tasks = [run_single_tool(call) for call in last_message.tool_calls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for idx, res in enumerate(results):
            if isinstance(res, Exception):
                call = last_message.tool_calls[idx]
                tool_messages.append(
                    ToolMessage(
                        content=f"Tool execution error: {str(res)}",
                        name=call["name"],
                        tool_call_id=call.get("id"),
                    )
                )
            else:
                tool_messages.append(res)

    return {"messages": tool_messages}


def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
    """Terminate the loop when no tool calls are pending."""
    last_message = state["messages"][-1]

    # Check if there are explicit tool calls requested
    if isinstance(last_message, AIMessage) and bool(getattr(last_message, "tool_calls", None)):
        return "tools"

    return "__end__"


# ---------------------------------------------------------------------------
# 3. Assemble Graph with In-Memory Checkpointer
# ---------------------------------------------------------------------------
workflow = StateGraph(AgentState)  # type: ignore[bad-specialization]

workflow.add_node("agent", call_model)
workflow.add_node("tools", execute_tools)

workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
workflow.add_edge("tools", "agent")

checkpointer = MemorySaver()
agent_app = workflow.compile(checkpointer=checkpointer)

# --- Sanity Assertions on Compiled Graph ---
expected_nodes = {"agent", "tools"}
actual_nodes = set(agent_app.nodes.keys())
assert expected_nodes.issubset(actual_nodes), f"Graph missing required nodes! Found: {actual_nodes}"


# ---------------------------------------------------------------------------
# 4. SSE Streaming Runner
# ---------------------------------------------------------------------------
def extract_clean_text(content) -> str:
    """Extract clean string text without Google signature/extras metadata."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict):
                # Only keep user-facing text, ignore 'extras', 'signature', etc.
                if part.get("type") == "text" or "text" in part:
                    parts.append(part.get("text", ""))
            elif hasattr(part, "text"):
                parts.append(part.text)
            else:
                parts.append(str(part))
        return "".join(parts).strip()
    return str(content).strip()


async def stream_agent_execution(
    user_query: str,
    thread_id: str = "default-session",
    tools: list[str] | None = None,
):
    """
    Streams clean, minimal events for the frontend:
    - tool_call: When the agent decides to invoke an external tool
    - tool_result: The output from the executed tool
    - message: The final synthesized AI answer
    """
    configurable: dict[str, Any] = {"thread_id": thread_id}
    if tools is not None:
        configurable["active_tools"] = tools

    config = {"configurable": configurable}
    input_message = HumanMessage(content=user_query)

    async for event in agent_app.astream(
        {"messages": [input_message]},
        config=config,
        stream_mode="updates"
    ):
        for node_name, state_update in event.items():
            messages = state_update.get("messages", [])

            for msg in messages:
                # 1. Agent initiated tool call(s)
                if isinstance(msg, AIMessage) and msg.tool_calls:
                    for call in msg.tool_calls:
                        yield json.dumps({
                            "type": "tool_call",
                            "tool": call["name"],
                            "args": call["args"]
                        })

                # 2. Tool executed and returned output
                elif isinstance(msg, ToolMessage):
                    yield json.dumps({
                        "type": "tool_result",
                        "tool": msg.name,
                        "output": msg.content
                    })

                # 3. Agent generated final conversational answer
                elif isinstance(msg, AIMessage):
                    clean_text = extract_clean_text(msg.content)
                    if clean_text:
                        yield json.dumps({
                            "type": "message",
                            "content": clean_text
                        })
