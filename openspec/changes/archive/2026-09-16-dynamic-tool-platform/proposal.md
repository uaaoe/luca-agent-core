## Why

Currently, agent tools are hardcoded directly within the agent workflow file (`app/agent.py`), tools are statically bound to the model at import time, and every tool is executed sequentially. Clients have no way to inspect which tools exist or selectively enable a subset of tools per request.

Transforming `luca-agent-core` into a plug-and-play tool platform enables modular tool authoring, automated tool discovery, runtime introspection via a queryable endpoint, and strict opt-in dynamic tool binding per session.

## What Changes

- **Tool Registry & Auto-Discovery**: Introduce a centralized `ToolRegistry` that automatically scans and imports tool modules placed in `app/tools/`.
- **Queryable Tools Endpoint (`GET /tools`)**: Expose a REST endpoint that returns a manifest of all registered tools, their docstrings, and JSON argument schemas.
- **Strict Opt-In Dynamic Tool Binding**: Update the SSE streaming pipeline (`POST /stream`) to accept an optional `tools` whitelist. By default, **no tools are enabled** unless explicitly requested by the client.
- **Concurrent & Resilient Tool Execution**: Update the agent graph execution node to run requested tool calls concurrently via `asyncio.gather` and capture exceptions gracefully without terminating the SSE stream.
- **Decouple Existing Tools**: Extract built-in demo tools (weather forecast and calculator) from `app/agent.py` into dedicated modules under `app/tools/`.

## Capabilities

### New Capabilities
- `tool-registry`: Dynamic registration, auto-import discovery from `app/tools/`, and client discovery endpoint (`GET /tools`).
- `dynamic-agent-execution`: Request-level dynamic tool binding in LangGraph, strict opt-in tool enablement, and concurrent resilient tool invocation.

### Modified Capabilities
<!-- None: Greenfield capabilities; no existing specs in the project. -->

## Impact

- **API Changes**:
  - New endpoint: `GET /tools` returning JSON list of registered tool manifests.
  - Updated payload for `POST /stream`: accepts optional `tools: list[str]`.
- **Core Architecture**:
  - `app/agent.py`: Tools are no longer statically bound at module level; execution node uses `asyncio.gather` with exception catching.
  - `app/tools/`: Transformed into a package hosting individual tool modules (`weather.py`, `calculator.py`, etc.) and the registry manager.
- **Dependencies**: No additional external dependencies required; uses existing `fastapi`, `pydantic`, `langchain-core`, and standard library `pkgutil`/`importlib`.
