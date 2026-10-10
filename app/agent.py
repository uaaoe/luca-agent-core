import asyncio
import json
from collections.abc import Sequence
from typing import Annotated, Any, Literal, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from app.config import settings
from app.tools.registry import registry


def get_llm():
    """Lazy initialize the Gemini LLM instance."""
    return ChatGoogleGenerativeAI(
        model=settings.model_name,
        google_api_key=settings.google_api_key or "placeholder_key",
        max_retries=2,
        request_timeout=15.0,
    )


def resolve_model(active_tools: Sequence[str] | None = None):
    """
    Bind tools to LLM if requested, otherwise return the raw LLM.
    Ensures zero tools are bound by default (strict opt-in).
    """
    model = get_llm()
    if active_tools:
        selected_tools = registry.get_tools(active_tools)
        if selected_tools:
            return model.bind_tools(selected_tools)
    return model


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
            except Exception as exc:  # noqa: BLE001
                # Dynamically registered tools can raise arbitrary runtime errors.
                return ToolMessage(
                    content=f"Tool execution error: {exc!s}",
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
                        content=f"Tool execution error: {res!s}",
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

    if isinstance(last_message, AIMessage) and bool(getattr(last_message, "tool_calls", None)):
        return "tools"

    return "__end__"


# ---------------------------------------------------------------------------
# 3. Assemble Graph with In-Memory Checkpointer
# ---------------------------------------------------------------------------
workflow = StateGraph(AgentState)

workflow.add_node("agent", call_model)
workflow.add_node("tools", execute_tools)

workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
workflow.add_edge("tools", "agent")

checkpointer = MemorySaver()
agent_app = workflow.compile(checkpointer=checkpointer)


# ---------------------------------------------------------------------------
# 4. SSE Streaming Runner
# ---------------------------------------------------------------------------
async def stream_agent_execution(
    user_query: str,
    thread_id: str = "default-session",
    tools: list[str] | None = None,
):
    """Streams clean events for the frontend."""
    settings.validate_api_keys()
    configurable: dict[str, Any] = {"thread_id": thread_id}
    if tools is not None:
        configurable["active_tools"] = tools

    config = {"configurable": configurable}
    input_message = HumanMessage(content=user_query)

    async for event in agent_app.astream(
        {"messages": [input_message]},
        config=config,
        stream_mode="values",
    ):
        for state_update in event.values():
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
