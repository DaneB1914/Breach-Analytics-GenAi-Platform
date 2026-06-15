from fastapi import FastAPI

from app.api.routes.health import router as health_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title="Breach Analytics GenAI Platform API",
        version="0.1.0",
        description="Backend API for a portfolio breach analytics platform.",
    )

    # Keep routes grouped by feature so future ETL and incident APIs stay organized.
    app.include_router(health_router)

    return app


app = create_app()
