import uvicorn

from app.config import settings


def main() -> None:
    """Entry point for the luca-agent-core CLI command."""
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.port)
