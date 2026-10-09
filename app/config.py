from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    port: int = 8000
    google_api_key: str = ""
    llm_provider: str = "gemini"
    model_name: str = "gemini-1.5-flash-lite"
    cors_origins: list[str] = ["*"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def validate_api_keys(self) -> None:
        """Validate API key presence and format when runtime execution starts."""
        key = self.google_api_key.strip()
        if not key:
            raise ValueError(
                "CRITICAL: GOOGLE_API_KEY is missing or empty. Please set it in your .env file or environment."
            )
        if len(key) < 25:
            raise ValueError("WARNING: GOOGLE_API_KEY appears truncated or invalid.")


settings = Settings()