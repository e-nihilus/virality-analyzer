from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Aurea Viral Intelligence"
    version: str = "0.1.0"
    debug: bool = True

    # Environment: "local" | "staging" | "production"
    environment: str = "local"

    uploads_dir: Path = Path(__file__).resolve().parents[3] / "uploads"

    # Storage backend: "local" for filesystem, "s3" for future cloud storage
    storage_backend: str = "local"

    # CORS — overridden per environment via AUREA_CORS_ORIGINS env var
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # Future: auth provider integration (Clerk JWT validation)
    auth_enabled: bool = False

    # Queue backend: "thread" for in-process (default), "redis" for RQ workers
    queue_backend: str = "thread"

    # Redis connection URL (used when queue_backend == "redis")
    redis_url: str = "redis://localhost:6379/0"

    model_config = {"env_prefix": "AUREA_"}


settings = Settings()

# Ensure uploads directory exists (local storage only)
if settings.storage_backend == "local":
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
