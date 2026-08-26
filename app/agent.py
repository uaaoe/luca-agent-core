import json
import operator
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, END
from app.tools import web_search_tool

class AgentState(TypedDict):
    input: str
    intermediate_steps: Annotated[list[str], operator.add]
    final_output: str

async def reasoner(state: AgentState):
    return {"intermediate_steps": [f"Reasoning over: {state['input']}"]}

async def execute_tool(state: AgentState):
    search_data = await web_search_tool(state["input"])
    return {
        "intermediate_steps": [f"Tool output: {search_data}"],
        "final_output": f"Final answer generated from: {search_data}"
    }

workflow = StateGraph(AgentState)
workflow.add_node("reason", reasoner)
workflow.add_node("action", execute_tool)
workflow.set_entry_point("reason")
workflow.add_edge("reason", "action")
workflow.add_edge("action", END)

agent_runner = workflow.compile()

async def stream_agent_execution(query: str):
    async for event in agent_runner.astream({"input": query}):
        for node_name, state_update in event.items():
            yield json.dumps({"node": node_name, "update": state_update})
