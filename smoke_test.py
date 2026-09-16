import json
from starlette.testclient import TestClient
from app.main import app


def run_smoke_test():
    print("Running Pre-Demo Sanity Check...")

    with TestClient(app) as client:
        # 1. Query GET /tools
        print("\n1. Testing GET /tools endpoint...")
        res = client.get("/tools")
        assert res.status_code == 200, f"FAILED: GET /tools returned {res.status_code}"
        tools_manifest = res.json()
        assert isinstance(tools_manifest, list), "FAILED: Manifest is not a list"
        tool_names = [t["name"] for t in tools_manifest]
        assert "get_weather_forecast" in tool_names, "FAILED: get_weather_forecast missing from /tools"
        assert "calculate_metric" in tool_names, "FAILED: calculate_metric missing from /tools"
        print(f"  ✓ Discovered {len(tools_manifest)} tools: {tool_names}")

        # 2. Test request without tools (strict opt-in: zero tool calls)
        print("\n2. Testing request without tools (strict opt-in)...")
        events_no_tools = []
        with client.stream("POST", "/stream", json={"message": "What is the weather in Barcelona?"}) as resp:
            assert resp.status_code == 200
            for line in resp.iter_lines():
                if line.startswith("data: ") and not line.startswith("data: [DONE]"):
                    try:
                        events_no_tools.append(json.loads(line[6:]))
                    except json.JSONDecodeError:
                        pass

        assert len(events_no_tools) > 0, "FAILED: No events emitted without tools"
        assert not any(e.get("type") == "tool_call" for e in events_no_tools), "FAILED: Tool called when none were requested!"
        assert any(e.get("type") == "message" for e in events_no_tools), "FAILED: No conversational response generated"
        print("  ✓ Zero tools invoked, direct conversational response generated")

        # 3. Test request with enabled tools (dynamic tool execution)
        print("\n3. Testing request with enabled tools (get_weather_forecast)...")
        events_with_tools = []
        with client.stream(
            "POST",
            "/stream",
            json={
                "message": "What is the weather in Barcelona?",
                "tools": ["get_weather_forecast"],
            }
        ) as resp:
            assert resp.status_code == 200
            for line in resp.iter_lines():
                if line.startswith("data: ") and not line.startswith("data: [DONE]"):
                    try:
                        events_with_tools.append(json.loads(line[6:]))
                    except json.JSONDecodeError:
                        pass

        assert len(events_with_tools) > 0, "FAILED: No events emitted with tools"
        assert any(e.get("type") == "tool_call" for e in events_with_tools), "FAILED: Expected tool_call event not emitted!"
        assert any(e.get("type") == "tool_result" for e in events_with_tools), "FAILED: Expected tool_result event not emitted!"
        assert any(e.get("type") == "message" for e in events_with_tools), "FAILED: Expected final message event not emitted!"
        print("  ✓ Dynamic tool executed and results returned")

    print("\nALL SANITY CHECKS PASSED: Demo is safe to present.")


if __name__ == "__main__":
    run_smoke_test()
