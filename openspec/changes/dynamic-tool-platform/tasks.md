## 1. Tool Registry & Auto-Discovery

- [ ] 1.1 Create `app/tools/registry.py` implementing `ToolRegistry` with `@registry.register`, tool lookup, and JSON schema manifest generation; verify via unit assertion that registered tools produce valid manifests
- [ ] 1.2 Implement `auto_discover()` in `app/tools/registry.py` using `pkgutil` to dynamically discover and import all tool modules in `app/tools/`; verify that newly created modules are automatically loaded
- [ ] 1.3 Migrate existing tools into `app/tools/weather.py` and `app/tools/calculator.py`, clean up unused `app/tools.py`, and verify `registry.list_tools()` returns both tools upon auto-discovery

## 2. Dynamic Agent Execution in LangGraph

- [ ] 2.1 Refactor `call_model` in `app/agent.py` to inspect `active_tools` from `RunnableConfig` and bind only requested tools (or raw LLM if none requested); verify that calling with empty tools produces an LLM without tool definitions
- [ ] 2.2 Refactor `execute_tools` in `app/agent.py` to resolve tools from `ToolRegistry`, invoke them concurrently with `asyncio.gather`, and catch exceptions into error `ToolMessage`s; verify with parallel tool call execution
- [ ] 2.3 Update `stream_agent_execution` in `app/agent.py` to accept `tools: list[str] | None = None` and forward it into `RunnableConfig`; verify execution streams correctly with and without tools

## 3. API Endpoints & Validation

- [ ] 3.1 Add `GET /tools` endpoint in `app/main.py` calling `registry.get_manifest()`; verify with an HTTP request that the endpoint returns the catalog of tool names, descriptions, and parameter schemas
- [ ] 3.2 Update `POST /stream` endpoint in `app/main.py` to accept optional `tools` in the request body, validate that all requested tool names exist in `ToolRegistry` (returning HTTP 400 for unknown tools), and pass `tools` to `stream_agent_execution`

## 4. End-to-End Verification & Documentation

- [ ] 4.1 Update `smoke_test.py` to test: (1) querying `GET /tools`, (2) sending a request without tools (verifying zero tool calls), and (3) sending a request with enabled tools (verifying dynamic tool execution)
- [ ] 4.2 Update `README.md` to document how to add new tools into `app/tools/` and how clients can query and enable tools via the API
