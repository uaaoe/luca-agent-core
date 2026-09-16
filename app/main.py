import json

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agent import stream_agent_execution
from app.config import settings
from app.tools.registry import registry

# Ensure tools are auto-discovered
registry.auto_discover()

app = FastAPI(title="Luca Agent Core", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class StreamRequest(BaseModel):
    model_config = {"extra": "allow"}
    message: str = ""
    thread_id: str = "default-session"
    tools: list[str] | None = None


@app.get("/health")
def health_check():
    return {"status": "ok", "app": "luca-agent-core", "provider": settings.llm_provider}


@app.get("/tools")
def get_tools():
    """Return manifest of all registered tools and their parameter schemas."""
    return registry.get_manifest()


@app.post("/stream")
async def run_pipeline(payload: StreamRequest):
    """
    Stream agent execution via SSE.
    Strict opt-in: tools must be explicitly requested in `payload.tools`.
    Validates that all requested tools exist in registry, returning 400 on unknown tools.
    """
    if payload.tools:
        for tool_name in payload.tools:
            if not registry.has_tool(tool_name):
                raise HTTPException(
                    status_code=400,
                    detail=f"Unknown tool requested: '{tool_name}'",
                )

    async def event_generator():
        try:
            async for chunk in stream_agent_execution(
                payload.message,
                thread_id=payload.thread_id,
                tools=payload.tools,
            ):
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as exc:
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
