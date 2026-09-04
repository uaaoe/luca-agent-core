import json
from typing import Annotated, Literal, Sequence, TypedDict
from langchain_core.messages import BaseMessage, HumanMessage, ToolMessage, AIMessage
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver

from app.config import settings

# ---------------------------------------------------------------------------
# 1. Reusable Tools
# ---------------------------------------------------------------------------
@tool
def get_weather_forecast(city: str) -> str:
    """Get the current weather forecast for a given city."""
    # Tool assertion: validate input before network calls
    assert city and isinstance(city, str), "Sanity Check: City must be a non-empty string"
    
    result = f"The weather in {city} is 26°C, mostly sunny."
    
    # Sanity Check: Ensure output contract is satisfied
    assert len(result) > 0, "Tool produced empty output"
    return result

@tool
def calculate_metric(expression: str) -> str:
    """Safely calculate basic mathematical expressions."""
    # Tool assertion: validate input before evaluation
    assert expression and isinstance(expression, str), "Sanity Check: Expression must be a non-empty string"

    try:
        allowed = {"__builtins__": {}}
        result = eval(expression, allowed, {})
        return f"Calculation result: {result}"
    except Exception as exc:
        return f"Calculation error: {str(exc)}"

tools = [get_weather_forecast, calculate_metric]
tools_by_name = {t.name: t for t in tools}

# ---------------------------------------------------------------------------
# 2. Gemini LLM Initialization & Tool Binding
# ---------------------------------------------------------------------------
llm = ChatGoogleGenerativeAI(
    model="gemini-3.5-flash-lite",
    google_api_key=settings.google_api_key,
    max_retries=2,
    request_timeout=15.0,
)

llm_with_tools = llm.bind_tools(tools)

# ---------------------------------------------------------------------------
# 3. Agent State & Nodes
# ---------------------------------------------------------------------------
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]

async def call_model(state: AgentState):
    """Invoke Gemini with full message history."""
    response = await llm_with_tools.ainvoke(state["messages"])
    return {"messages": [response]}

async def execute_tools(state: AgentState):
    """Execute tools requested by Gemini."""
    last_message = state["messages"][-1]
    tool_messages = []

    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        for tool_call in last_message.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            tool_id = tool_call["id"]

            if tool_name in tools_by_name:
                selected_tool = tools_by_name[tool_name]
                tool_output = await selected_tool.ainvoke(tool_args)
            else:
                tool_output = f"Error: Tool '{tool_name}' not found."

            tool_messages.append(
                ToolMessage(
                    content=str(tool_output),
                    name=tool_name,
                    tool_call_id=tool_id,
                )
            )

    return {"messages": tool_messages}

def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
    """Terminate the loop when no tool calls are pending."""
    last_message = state["messages"][-1]
    
    # Check if there are explicit tool calls requested
    if isinstance(last_message, AIMessage) and bool(getattr(last_message, "tool_calls", None)):
        return "tools"
    
    return END


# ---------------------------------------------------------------------------
# 4. Assemble Graph with In-Memory Checkpointer
# ---------------------------------------------------------------------------
workflow = StateGraph(AgentState)

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
# 5. SSE Streaming Runner
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


async def stream_agent_execution(user_query: str, thread_id: str = "default-session"):
    """
    Streams clean, minimal events for the frontend:
    - tool_call: When the agent decides to invoke an external tool
    - tool_result: The output from the executed tool
    - message: The final synthesized AI answer
    """
    config = {"configurable": {"thread_id": thread_id}}
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
