# ⚡ Luca Agent Core

A high-velocity, deterministic AI agent backend built for rapid prototyping and zero-friction deployment. Built with **FastAPI**, **LangGraph**, and managed via **uv**.

---

## 🚀 Key Features

* **⚡ Ultra-Fast Environment:** Dependency management, Python runtime pinning (3.12), and lockfile handling powered by `uv`.
* **🧠 Graph-Based Orchestration:** State-driven execution workflows with typed memory state using `LangGraph`.
* **📡 Real-Time SSE Streaming:** Server-Sent Events (SSE) streaming direct from the graph execution nodes.
* **📦 Production-Ready Containerization:** Multi-stage Docker setup optimized for instant deployment to Railway, Render, or Fly.io.

---

## 📁 Repository Structure

```text
luca-agent-core/
├── app/
│   ├── __init__.py
│   ├── config.py       # Pydantic environment configuration
│   ├── tools.py        # Reusable agent tool integrations
│   ├── agent.py        # LangGraph state machine & streaming runner
│   └── main.py         # FastAPI endpoints (Health, SSE stream)
├── .env.example
├── Dockerfile          # Slim uv-cached container definition
├── pyproject.toml      # Project manifest
├── uv.lock             # Deterministic lockfile
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

## 🧪 Testing Endpoints

### 1. Health Check
```bash
curl http://localhost:8000/health
```

### 2. Stream Pipeline Execution (SSE)
```bash
curl -N -X POST http://localhost:8000/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Run Barcelona pipeline"}'
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
3. Add any required environment variables (`OPENAI_API_KEY`, etc.) in the dashboard settings.

---

## 📄 License
MIT License. Free to use, adapt, and build upon.
