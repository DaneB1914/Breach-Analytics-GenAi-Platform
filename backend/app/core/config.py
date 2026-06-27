import os
from functools import lru_cache

from pydantic import BaseModel

DEFAULT_DATABASE_URL = (
    "postgresql+psycopg://breach_user:breach_password@localhost:5432/breach_analytics"
)


class Settings(BaseModel):
    """Runtime settings loaded from environment variables."""

    database_url: str = DEFAULT_DATABASE_URL
    openai_api_key: str | None = None
    upload_dir: str = "uploads"


@lru_cache
def get_settings() -> Settings:
    # Read environment variables in one place so future database code stays simple.
    return Settings(
        database_url=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        upload_dir=os.getenv("UPLOAD_DIR", "uploads"),
    )
