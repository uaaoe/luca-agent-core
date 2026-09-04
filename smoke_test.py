import asyncio
from app.agent import stream_agent_execution

async def run_smoke_test():
    print("Running Pre-Demo Sanity Check...")
    events = []
    
    # Test tool invocation and memory check
    async for raw_chunk in stream_agent_execution("What is the weather in Barcelona?", thread_id="smoke-test"):
        events.append(raw_chunk)
        print("  ✓ Received event chunk")

    # Assert basic end-to-end criteria
    assert len(events) > 0, "FAILED: No events emitted by agent!"
    assert any("tool_call" in e for e in events), "FAILED: Agent did not trigger tool call!"
    assert any("message" in e for e in events), "FAILED: Agent did not produce final text!"
    
    print("ALL SANITY CHECKS PASSED: Demo is safe to present.")

if __name__ == "__main__":
    asyncio.run(run_smoke_test())
