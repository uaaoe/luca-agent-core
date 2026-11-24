# Luca Agent Core

## Architecture

- `app/main.py` is the FastAPI entry point. Its lifespan initializes tool discovery, and the API exposes `/health`, `/tools`, and `/stream` for server-sent events.
- `app/agent.py` defines typed LangGraph state, Gemini model binding, asynchronous tool execution, event streaming, and in-memory checkpointing with `MemorySaver`.
- `app/config.py` uses Pydantic Settings for runtime configuration. See `.env.example` for configuration names.
- `app/tools/registry.py` owns tool registration, discovery, lookup, and schema manifests. Tool implementations live in `app/tools/`, including the calculator and its AST-based expression evaluator.
- `src/luca_agent_core/` contains the package entry point. The Dockerfile serves `app.main:app` with Uvicorn.
- `tests/` contains pytest unit tests for the calculator and registry. `smoke_test.py` is a separate live Gemini check that requires network access and credentials.

## Development and validation

- The package declares Python 3.11 or newer. `.python-version` and the Docker image use Python 3.12.
- Manage Python dependencies with uv. Keep dependency declarations in `pyproject.toml` and commit the corresponding `uv.lock` changes when modifying dependencies.
- Run `uv sync --locked`, then `uv run --no-sync ruff check .` and `uv run pytest -q`. GitHub Actions also checks app import and tool discovery with a dummy Google API key, then builds the Docker image.
- Prefer deterministic tests with fake model or tool dependencies for graph and API behavior. Use a dummy key for local import checks that do not call Gemini and keep real credentials out of source, tests, and logs.
- Follow the repository’s OpenSpec workflow for behavior changes. Current specifications live in `openspec/specs/`, completed changes in `openspec/changes/archive/`, and workflow definitions in `.agents/`.

## Accelerator practice

During accelerator sessions, follow the mentoring workflow in the global instructions. Use the [curriculum](https://app.notion.com/p/41e85d013672812ca9e6d99280a74373) and the existing [Learning Journal](https://app.notion.com/p/42285d01367281c39fbfe3ef57629c1e) for daily agendas and progress. Reconcile the latest entry with local changes and available test or CI evidence before selecting the first unfinished task. Agree on acceptance criteria, let Luca implement independently, and review the diff with focused checks before recording a short journal update.
