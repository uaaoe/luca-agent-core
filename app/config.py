import json
from contextlib import suppress
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    port: int = 8000
    google_api_key: str = ""
    model_name: str = "gemini-3.5-flash-lite"
    cors_origins: list[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                with suppress(json.JSONDecodeError, TypeError):
                    parsed = json.loads(v)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed]
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    def validate_api_keys(self) -> None:
        """Validate API key presence and format when runtime execution starts."""
        key = self.google_api_key.strip()
        if not key:
            raise RuntimeError(
                "CRITICAL: GOOGLE_API_KEY is missing or empty in .env! "
                "Please configure a valid Google AI API key."
            )
        if len(key) < 25:
            raise RuntimeError(
                "WARNING: GOOGLE_API_KEY appears truncated or invalid (expected at least 25 characters)."
            )


settings = Settings()
