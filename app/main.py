from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from app.config import settings
from app.agent import stream_agent_execution

app = FastAPI(title="Luca Agent Core", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "ok", "app": "luca-agent-core", "env": settings.app_env}

@app.post("/stream")
async def run_pipeline(request: Request):
    payload = await request.json()
    user_query = payload.get("message", "")

    async def event_generator():
        async for chunk in stream_agent_execution(user_query):
            yield f"data: {chunk}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
