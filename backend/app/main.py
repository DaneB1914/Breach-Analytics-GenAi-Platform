from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.core.config import get_settings


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    settings = get_settings()

    app = FastAPI(
        title="Breach Analytics GenAI Platform API",
        version="0.1.0",
        description="Backend API for a portfolio breach analytics platform.",
    )

    # Store settings on app.state so later database code can reuse the same config.
    app.state.database_url = settings.database_url

    # Keep routes grouped by feature so future ETL and incident APIs stay organized.
    app.include_router(health_router)

    return app


app = create_app()
