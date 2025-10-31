"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    logger.info(
        "Starting DriftGuards application",
        version=settings.app_version,
        environment=settings.environment,
    )

    # Startup tasks
    # TODO: Initialize database connections, load models, etc.

    yield

    # Shutdown tasks
    logger.info("Shutting down DriftGuards application")
    # TODO: Close database connections, cleanup resources


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""

    app = FastAPI(
        title=settings.app_name,
        description="AWS IaC Drift Analyzer with AI-powered insights and remediation",
        version=settings.app_version,
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.is_development else ["https://yourdomain.com"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check endpoint
    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {
            "status": "healthy",
            "version": settings.app_version,
            "environment": settings.environment,
        }

    # Root endpoint
    @app.get("/")
    async def root() -> dict[str, str]:
        """Root endpoint."""
        return {
            "app": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs" if settings.is_development else "disabled",
        }

    # Exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Any, exc: Exception) -> JSONResponse:
        """Global exception handler."""
        logger.error(
            "Unhandled exception",
            path=str(request.url),
            error=str(exc),
            exc_info=exc,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    # TODO: Include API routers
    # from app.api.v1 import drifts, remediations, analytics, policies
    # app.include_router(drifts.router, prefix=f"{settings.api_prefix}/drifts", tags=["drifts"])
    # app.include_router(remediations.router, prefix=f"{settings.api_prefix}/remediations", tags=["remediations"])
    # app.include_router(analytics.router, prefix=f"{settings.api_prefix}/analytics", tags=["analytics"])
    # app.include_router(policies.router, prefix=f"{settings.api_prefix}/policies", tags=["policies"])

    logger.info("FastAPI application created successfully")
    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
    )
