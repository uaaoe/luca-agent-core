from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_env: str = "development"
    port: int = 8000
    google_api_key: str = ""
    llm_provider: str = "gemini"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()

# --- Sanity Assertions ---
# 1. Ensure the key was actually parsed from .env
assert bool(settings.google_api_key.strip()), "CRITICAL: GOOGLE_API_KEY is missing or empty in .env!"

# 2. Check for realistic token length (Google API keys are at least 30+ characters)
assert len(settings.google_api_key.strip()) > 25, "WARNING: GOOGLE_API_KEY appears truncated or invalid."
