## Context

See `proposal.md` for motivation. Currently, tools (`get_weather_forecast`, `calculate_metric`) are defined inline in `app/agent.py` and bound statically to the `ChatGoogleGenerativeAI` instance.

## Goals / Non-Goals

**Goals:**
- Provide a clean `ToolRegistry` that automatically registers all tools placed in `app/tools/`.
- Provide a `GET /tools` endpoint exposing tool names, descriptions, and JSON Schema parameters.
- Enable dynamic request-scoped tool filtering via `POST /stream` with strict opt-in (default: zero tools).
- Enable concurrent tool execution via `asyncio.gather` with resilient error handling.
- Modularize existing tools into individual files under `app/tools/`.

**Non-Goals:**
- Dynamic remote tool loading (e.g. fetching tools over the network or hot-reloading at runtime without server restart).
- Multi-agent routing / subgraphs (remains a single LangGraph agent).
- Complex authorization / RBAC per tool (tools requested by client are validated strictly for existence in the registry).

## Decisions

### Decision 1: Registry Singleton and Auto-Discovery
- **Approach**: Create `app/tools/registry.py` providing a `ToolRegistry` class and singleton `registry`. It provides a `@registry.register` decorator (or registers LangChain `@tool` instances) and an `auto_discover()` function using `pkgutil.iter_modules` and `importlib.import_module` to dynamically load all modules in `app/tools/`.
- **Alternative considered**: Explicit manual registration in `app/tools/__init__.py`. Rejected because auto-discovery fulfills the requirement that adding a new file to `app/tools/` automatically makes it available without editing index files.

### Decision 2: Schema Extraction via LangChain BaseTool
- **Approach**: Registered tools are instances of LangChain `BaseTool`. `registry.get_manifest()` extracts:
  - `name`: `tool.name`
  - `description`: `tool.description`
  - `parameters`: `tool.args_schema.model_json_schema()` (or fallback to empty object if no args).
- **Alternative considered**: Custom manual JSON schema definition. Rejected as LangChain `@tool` / Pydantic already generates standards-compliant JSON Schemas automatically.

### Decision 3: Dynamic Tool Binding via LangGraph RunnableConfig
- **Approach**: Pass `active_tools: list[str]` via `RunnableConfig` (`config["configurable"]["active_tools"]`).
  - In `call_model(state, config)`: Inspect `config["configurable"].get("active_tools")`. If present and non-empty, retrieve the matching tools from `registry` and bind them to the LLM (`llm.bind_tools(selected_tools)`). If empty or None, invoke the raw `llm`.
  - In `execute_tools(state, config)`: Resolve tool instances from `registry` and execute pending tool calls concurrently using `asyncio.gather(..., return_exceptions=True)`.
- **Alternative considered**: Recompiling the StateGraph on every request. Rejected because compiling per request adds unnecessary overhead, whereas `RunnableConfig` cleanly parameterizes the graph at runtime.

### Decision 4: Opt-In Request Validation in FastAPI
- **Approach**: Update `POST /stream` payload parsing (or Pydantic `StreamRequest` model) to include `tools: list[str] | None = None`. If any requested tool name is not registered in `registry`, immediately return HTTP 400 Bad Request before initiating the stream.
- **Alternative considered**: Silently ignoring unknown tool names. Rejected because failing fast informs client developers of typos or missing tools upfront.

## Risks / Trade-offs

- **[Risk] Module import side-effects during auto-discovery** → *Mitigation*: Auto-discovery is scoped strictly to `app.tools.*` package modules, and tool modules must only declare tools and imports, avoiding top-level side effects.
- **[Risk] Unhandled tool exception crashing the stream** → *Mitigation*: Tool execution wraps each tool call with exception handling and returns a `ToolMessage` containing error details to the LLM, preserving the SSE stream.
- **[Risk] Rate limits or concurrent external API calls** → *Mitigation*: `asyncio.gather` runs calls in parallel, but individual tools can implement internal semaphores or rate limiters if interacting with constrained external APIs.
