"""
Blueprint Backend — FastAPI Application Factory

App creation, middleware (CORS, rate limiting, request ID logging), router registration.
Run with: uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.config import settings, log
from app.api import codegen, research, journeys, figma

# Rate limiter — global, per-IP
limiter = Limiter(key_func=get_remote_address)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Log the X-Request-Id header from every incoming request.

    The frontend includes X-Request-Id on every fetch call.
    This middleware logs it so REST errors can be correlated with backend logs.
    """

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-Id", "none")
        log(
            "INFO",
            "request received",
            method=request.method,
            path=request.url.path,
            request_id=request_id,
        )
        response = await call_next(request)
        return response


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Steps:
        1. Create FastAPI instance with title, version, description
        2. Add CORS middleware (origins from settings.cors_origins)
        3. Add request ID logging middleware
        4. Add rate limiting (slowapi)
        5. Register routers (research, journeys)
        6. Return the app
    """
    app = FastAPI(
        title="Blueprint API",
        version="0.1.0",
        description="Product & market research tool — competitive intelligence via SSE streaming.",
    )

    # CORS
    origins = [origin.strip() for origin in settings.cors_origins.split(",")]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request ID logging
    app.add_middleware(RequestIdMiddleware)

    # Rate limiting (applied per-endpoint via decorator, not globally)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Routers
    app.include_router(research.router)
    app.include_router(journeys.router)
    app.include_router(figma.router)
    app.include_router(codegen.router)

    return app


app = create_app()


@app.get("/api/health")
async def health_check():
    """
    GET /api/health

    Returns: { "status": "ok", "version": "0.1.0" }
    """
    return {"status": "ok", "version": "0.1.0"}
