"""FastAPI application factory."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .errors import APIError
from .routes import protocols, sessions


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="Assessment Engine API",
        description="Natural Language Assessment Engine REST API",
        version="0.2.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Error handlers
    @app.exception_handler(APIError)
    async def api_error_handler(request: Request, exc: APIError):
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.message, "code": exc.code},
        )

    # Health check
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "version": "0.2.0"}

    # Include routers
    app.include_router(protocols.router, prefix="/protocols", tags=["protocols"])
    app.include_router(sessions.router, prefix="/sessions", tags=["sessions"])

    return app
