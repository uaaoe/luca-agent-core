# 🛡️ SentinelGraph (formerly Luca Agent Core)

A high-assurance, deterministic multi-agent runtime featuring a **Supervisor Orchestrator**, **Programmatic Policy Guard**, and **Human-in-the-Loop (HITL)** interruption checkpoints. Built with **FastAPI**, **LangGraph v1.2**, persistent **SQLite Checkpoint Storage**, and managed via **uv**.

---

## 🚀 Key Features

* **🧭 Supervisor Intent & Risk Classifier:** Inspects incoming requests to classify domain intent and categorize risk (`SAFE`, `GUARDED`, `CRITICAL`).
* **🛡️ Programmatic Policy Guard:** Enforces deterministic contract validations, boundary checks, and hard circuit breakers on tool execution.
* **⏸️ Human-in-the-Loop (HITL) Checkpoint Interruption:** Pauses high-risk operations at the checkpointer level, yielding structured clearance requests for human authorization.
* **💾 Local SQLite Checkpointer:** Persists thread states, messages, and pending approval interrupts locally (`data/checkpoints.db`) across server restarts.
* **📡 Real-Time SSE Streaming:** Server-Sent Events (SSE) stream fine-grained events (`supervisor`, `policy_check`, `hitl_required`, `tool_call`, `tool_result`, `message`).
* **🖥️ Built-In Live Visualizer (`/demo`):** Dark-mode interactive operator console with real-time node state animation, audit log terminal, and one-click HITL approval modal.
* **🔒 Simulated Demo Sandbox:** Strict simulation boundaries for all side-effecting operations (e.g. fund allocation simulator, container scaling). No real financial accounts or cloud resources are touched.

---

## 📁 Repository Structure

```text
luca-agent-core/
├── app/
│   ├── __init__.py
│   ├── config.py       # Pydantic environment configuration & safety assertions
│   ├── policy.py       # Deterministic policy engine & boundary checks
│   ├── tools.py        # Sandboxed tools with demo simulation banners
│   ├── agent.py        # Supervisor + Worker + Policy Guard + HITL StateGraph
│   ├── main.py         # FastAPI endpoints (/stream, /resume, /state, /demo)
│   └── static/
│       └── index.html  # Interactive operator visualizer & HITL approval UI
├── data/
│   └── checkpoints.db  # Local SQLite checkpointer database (auto-created)
├── smoke_test.py       # End-to-end multi-agent sanity test
├── .env.example
├── Dockerfile          # Slim uv-cached container definition
├── pyproject.toml      # Project manifest
├── uv.lock             # Deterministic lockfile
└── README.md
```

---

## 🛠️ Quickstart

### 1. Installation & Environment

```bash
# Clone the repository
git clone https://github.com/your-username/luca-agent-core.git
cd luca-agent-core

# Configure your Gemini API key in .env
cp .env.example .env
# Ensure GOOGLE_API_KEY=your_key is in .env

# Sync dependencies with uv
uv sync
```

### 2. Pre-Demo Smoke Test

Run the automated end-to-end verification script:
```bash
uv run python smoke_test.py
```
This test asserts:
- Autonomous execution of safe telemetry queries.
- Automatic triggering of the HITL interrupt on critical actions.
- SQLite persistence of paused checkpoints.
- Programmatic resumption upon operator approval.
- Enforcement of policy circuit-breakers when bounds are exceeded.

### 3. Start the Server & Visualizer

```bash
uv run uvicorn app.main:app --reload --port 8000
```

Open your browser to:
👉 **`http://localhost:8000/demo`** (or `http://localhost:8000/`)

---

## 📡 API Endpoints

### 1. `POST /stream`
Initiates a streaming execution pipeline via Server-Sent Events.
```bash
curl -N -X POST http://localhost:8000/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "Query cluster telemetry for CPU and memory.", "thread_id": "session-1"}'
```

### 2. `POST /resume`
Resumes an interrupted execution thread after human operator review.
```bash
curl -N -X POST http://localhost:8000/resume \
  -H "Content-Type: application/json" \
  -d '{"thread_id": "session-1", "approved": true, "feedback": "Approved by incident commander"}'
```

### 3. `GET /threads/{thread_id}/state`
Inspects current graph status and checks whether an approval interrupt is pending.
```bash
curl http://localhost:8000/threads/session-1/state
```

### 4. `GET /health`
Returns system status, active LLM provider, and sandbox safety verification flag.

---

## 🎯 Live Demonstration & Presentation Guide

When presenting SentinelGraph:

1. **The Core Philosophy:**
   *"Autonomous agents are powerful, but production and enterprise adoption are stalled by unpredictable side-effects, unauthorized operations, and lack of deterministic boundaries."*
2. **The Architecture:**
   *Show `/demo` dashboard.* Point out the 4-stage pipeline:
   - **Supervisor** (Risk classification)
   - **Worker LLM** (Gemini 3.5 Flash Lite)
   - **Deterministic Policy Guard** (Strict programmatic rules)
   - **HITL Checkpoint Gate** (LangGraph interrupt + SQLite persistence)
3. **Interactive Demo Scenarios:**
   - Click **Preset 1 (Telemetry)**: Show instant autonomous clearance (`SAFE`).
   - Click **Preset 3 (Emergency Disbursement)**: Show the Supervisor flagging `CRITICAL`, the Policy Guard pausing at the SQLite checkpoint, and the glowing **HITL Approval Modal** popping up.
   - Click **Authorize (Simulated)**: Demonstrate execution resuming live via `POST /resume` and recording the cryptographically logged simulated ledger entry.
   - Click **Preset 4 (Policy Breach)**: Show the circuit breaker outright blocking an excessive €850k request without operator intervention.
4. **Summary:**
   *"SentinelGraph demonstrates that autonomous agent velocity does not have to come at the expense of safety, auditability, and human control."*


---

## 📄 License
MIT License. Free to use, adapt, and build upon.
