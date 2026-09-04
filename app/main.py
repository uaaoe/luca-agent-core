import json
import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

from app.agent import (
    get_thread_state_info,
    resume_agent_execution,
    stream_agent_execution,
)
from app.config import settings

app = FastAPI(
    title="SentinelGraph",
    description="High-Assurance Deterministic Multi-Agent Runtime with Policy Guard & HITL Interruption",
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_INDEX = Path(__file__).parent / "static" / "index.html"


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "app": "sentinel-graph",
        "provider": settings.llm_provider,
        "simulation_mode": settings.simulation_mode,
        "checkpoints_db": settings.checkpoints_db_path,
    }


@app.get("/")
@app.get("/demo")
def serve_demo():
    """Serves the SentinelGraph Interactive Visualizer Dashboard."""
    if STATIC_INDEX.exists():
        return FileResponse(STATIC_INDEX)
    return {"error": "Demo frontend not found at app/static/index.html"}


@app.post("/stream")
async def run_pipeline(request: Request):
    """Initiates a streaming execution run for a user query."""
    payload = await request.json()
    user_query = payload.get("message", "")
    thread_id = payload.get("thread_id", "default-session")

    async def event_generator():
        try:
            async for chunk in stream_agent_execution(user_query, thread_id=thread_id):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as exc:
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/resume")
async def resume_pipeline(request: Request):
    """Resumes an interrupted execution thread with Human-in-the-Loop decision."""
    payload = await request.json()
    thread_id = payload.get("thread_id")
    approved = bool(payload.get("approved", False))
    feedback = str(payload.get("feedback", ""))

    if not thread_id:
        return {"error": "Missing 'thread_id' in resume payload"}

    async def event_generator():
        try:
            async for chunk in resume_agent_execution(thread_id, approved=approved, feedback=feedback):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as exc:
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/threads/{thread_id}/state")
async def thread_state(thread_id: str):
    """Inspects the thread's checkpoint state and any pending operator approval requests."""
    return await get_thread_state_info(thread_id)
