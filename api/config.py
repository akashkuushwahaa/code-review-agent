"""API configuration (pydantic-settings)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Code Review Agent — Dashboard API"
    app_version: str = "0.1.0"

    # Same SQLite file the agent writes to (shared volume in Docker).
    review_db_path: str = "findings.db"

    # A snapshot of eval.py's output. Refresh with:
    #   python eval.py --json api/eval_snapshot.json
    eval_path: str = "api/eval_snapshot.json"

    # The Next.js dev/prod origin, for CORS.
    allowed_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
