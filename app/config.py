import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_env: str = "development"
    port: int = 8000
    google_api_key: str = ""
    llm_provider: str = "gemini"
    checkpoints_db_path: str = "data/checkpoints.db"
    simulation_mode: bool = True  # Strict demo sandboxing flag

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()

# Ensure local storage directory exists
os.makedirs(os.path.dirname(settings.checkpoints_db_path) or ".", exist_ok=True)

# --- Sanity Assertions ---
# 1. Ensure the key was actually parsed from .env
assert bool(settings.google_api_key.strip()), "CRITICAL: GOOGLE_API_KEY is missing or empty in .env!"

# 2. Check for realistic token length (Google API keys are at least 30+ characters)
assert len(settings.google_api_key.strip()) > 25, "WARNING: GOOGLE_API_KEY appears truncated or invalid."

