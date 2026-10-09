# ⚡ Luca Agent Core

A high-velocity, deterministic AI agent backend built for rapid prototyping and zero-friction deployment. Built with **FastAPI**, **LangGraph**, and managed via **uv**.

---

## 🚀 Key Features

* **⚡ Ultra-Fast Environment:** Dependency management, Python runtime pinning (3.12), and lockfile handling powered by `uv`.
* **🧠 Graph-Based Orchestration:** State-driven execution workflows with typed memory state using `LangGraph`.
* **🛠️ Dynamic Tool Platform:** Auto-discovery plugin architecture for tools in `app/tools/` with strict request-scoped opt-in tool binding.
* **📡 Real-Time SSE Streaming:** Server-Sent Events (SSE) streaming direct from the graph execution nodes.
* **📦 Production-Ready Containerization:** Multi-stage Docker setup optimized for instant deployment to Railway, Render, or Fly.io.

---

## 📁 Repository Structure

```text
luca-agent-core/
├── app/
│   ├── __init__.py
│   ├── config.py           # Pydantic environment configuration
│   ├── tools/              # Dynamic tool platform
│   │   ├── __init__.py
│   │   ├── registry.py     # ToolRegistry & auto-discovery engine
│   │   ├── weather.py      # Weather forecast tool
│   │   └── calculator.py   # Metric calculation tool
│   ├── agent.py            # LangGraph state machine & dynamic tool binding
│   └── main.py             # FastAPI endpoints (Health, Tools catalog, SSE stream)
├── smoke_test.py           # Live end-to-end sanity check
├── .env.example
├── Dockerfile              # Slim uv-cached container definition
├── pyproject.toml          # Project manifest
├── uv.lock                 # Deterministic lockfile
└── README.md
```

---

## 🛠️ Quickstart

### Prerequisites

* Install [`uv`](https://astral.sh/uv/):
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

### Installation & Local Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/luca-agent-core.git
   cd luca-agent-core
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```

3. **Install dependencies and sync lockfile:**
   ```bash
   uv sync
   ```

4. **Start the local development server:**
   ```bash
   uv run uvicorn app.main:app --reload --port 8000
   ```

The API will be live at `http://localhost:8000`. Interactive OpenAPI documentation is accessible at `http://localhost:8000/docs`.

---

## 🧩 Dynamic Tool Platform

Tools in `luca-agent-core` are modular, auto-discovered, and strictly opt-in per request.

### Adding a New Tool

To add a new tool, create a new `.py` file in `app/tools/` (e.g. `app/tools/crypto.py`). Use `@registry.register` and LangChain's `@tool` decorator:

```python
from langchain_core.tools import tool
from app.tools.registry import registry

@registry.register
@tool
def get_crypto_price(symbol: str) -> str:
    """Fetch the latest spot price for a cryptocurrency symbol."""
    assert symbol and isinstance(symbol, str), "Symbol must be a non-empty string"
    # Execute lookup logic
    return f"Current price of {symbol.upper()}: $65,000 USD"
```

The tool registry will automatically discover and load your module on startup without requiring changes to any index or configuration file.

---

## 🧪 Testing Endpoints

### 1. Health Check
```bash
curl http://localhost:8000/health
```

### 2. Query Available Tools Catalog
Retrieve the manifest of all registered tools along with their docstrings and JSON parameter schemas:
```bash
curl http://localhost:8000/tools
```
Response:
```json
[
  {
    "name": "calculate_metric",
    "description": "Safely calculate basic mathematical expressions.",
    "parameters": { ... }
  },
  {
    "name": "get_weather_forecast",
    "description": "Get the current weather forecast for a given city.",
    "parameters": { ... }
  }
]
```

### 3. Stream Execution Without Tools (Default / Strict Opt-In)
By default, requests run with zero tools bound, ensuring direct conversational responses:
```bash
curl -N -X POST http://localhost:8000/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello, who are you?"}'
```

### 4. Stream Execution With Explicit Tools
Clients selectively enable tools by providing a `tools` whitelist array in the request body. Unknown tool names return `HTTP 400 Bad Request`.
```bash
curl -N -X POST http://localhost:8000/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the weather in Barcelona right now?",
    "tools": ["get_weather_forecast"]
  }'
```

---

## 🐳 Docker Deployment

Build and run the container locally:

```bash
docker build -t luca-agent-core .
docker run -p 8000:8000 --env-file .env luca-agent-core
```

### Deploy to Cloud (Railway / Render / Fly.io)
1. Push repository to GitHub.
2. Link the repository directly on your deployment platform.
3. Add the required `GOOGLE_API_KEY` environment variable in the dashboard settings.

---

## Sanity Assertions & Smoke Checks
This project uses **Sanity Assertions** and a live **Smoke Check** to catch configuration, graph-wiring, and tool-contract problems before a demo to avoid creating unnecessary friction.

### Why Use Assertions Here?

1. **Catch Configuration Failures at Startup:** Catch missing API keys or invalid environment settings on boot rather than during an active user stream.
2. **Prevent Graph Routing Drift:** Catch misspelled or disconnected LangGraph node names immediately after compilation.
3. **Guard Tool Output Contracts:** Prevent tools from silently returning `None` or empty strings, which breaks downstream LLM reasoning loops.
4. **Pre-Demo Confidence:** A single smoke script verifies the entire execution loop (LLM connection, tool catalog, opt-in execution, and streaming).

### Key Assertion Patterns Implemented

#### 1. Startup & Config Guardrails (`app/config.py`)
Checks that `GOOGLE_API_KEY` is present and appears complete before the application starts.

#### 2. Graph Wiring Verification (`app/agent.py`)
Confirms that compiled graphs contain all target nodes referenced in conditional edges.

#### 3. Tool Boundary Checks (`app/tools/*.py`)
Checks tool inputs and output contracts before results are returned to the agent graph.

#### Pre-Demo Smoke Test (`smoke_test.py`)
Run this single command before running or demoing the application:
```bash
uv run python smoke_test.py
```

The smoke check requires a valid `GOOGLE_API_KEY` in `.env` and network access to Gemini. It executes a 3-stage validation:
- Queries `GET /tools` and verifies registered tool schemas.
- Tests `POST /stream` with no tools, confirming zero tool calls and direct conversational synthesis.
- Tests `POST /stream` with an enabled tool, verifying tool invocation, tool result emission, and final synthesis.

---

## 📄 License
MIT License. Free to use, adapt, and build upon.
