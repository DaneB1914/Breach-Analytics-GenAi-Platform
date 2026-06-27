from fastapi import FastAPI

from app.api.routes.alerts import router as alerts_router
from app.api.routes.events import router as events_router
from app.api.routes.health import router as health_router
from app.api.routes.incidents import router as incidents_router
from app.api.routes.uploads import router as uploads_router
from app.api.routes.workflow import router as workflow_router
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
    app.include_router(events_router)
    app.include_router(alerts_router)
    app.include_router(incidents_router)
    app.include_router(uploads_router)
    app.include_router(workflow_router)

    return app


app = create_app()
