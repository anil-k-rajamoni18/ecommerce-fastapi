"""
main.py — FastAPI application entry point.

Responsibilities:
  - Create the FastAPI app instance
  - Register lifespan (startup / shutdown)
  - Mount all routers under /api/v1
  - Configure CORS, global exception handlers
  - Expose /health endpoint
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import check_db_connection, engine

logger = logging.getLogger(__name__)

# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs startup logic before yield, shutdown logic after.
    - Startup : verify DB connectivity, log banner
    - Shutdown: dispose DB connection pool gracefully
    """
    # ── Startup ──────────────────────────────────────────────────────────────
    logger.info("🚀  Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)

    db_ok = await check_db_connection()
    if not db_ok:
        logger.critical("Cannot reach the database. Check DATABASE_URL.")
        raise RuntimeError("Database unreachable on startup.")

    logger.info("Database connection verified.")
    logger.info("API prefix: %s", settings.API_PREFIX)
    logger.info("Debug mode: %s", settings.DEBUG)

    yield  # ←── Application runs here

    # ── Shutdown ─────────────────────────────────────────────────────────────
    logger.info("Shutting down %s. Disposing DB pool…", settings.APP_NAME)
    await engine.dispose()
    logger.info("Database pool closed. Goodbye.")


# ── App factory ───────────────────────────────────────────────────────────────

def create_application() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "Production-grade E-Commerce REST API built with FastAPI, "
            "SQLAlchemy (async), PostgreSQL, and JWT authentication."
        ),
        docs_url=f"{settings.API_PREFIX}/docs",
        redoc_url=f"{settings.API_PREFIX}/redoc",
        openapi_url=f"{settings.API_PREFIX}/openapi.json",
        lifespan=lifespan,
        # Disable default 422 detail leakage in production
        debug=settings.DEBUG,
    )

    # ── Middleware ────────────────────────────────────────────────────────────
    _register_middleware(app)

    # ── Exception handlers ────────────────────────────────────────────────────
    _register_exception_handlers(app)

    # ── Routers ───────────────────────────────────────────────────────────────
    _register_routers(app)

    return app


# ── Middleware ────────────────────────────────────────────────────────────────

def _register_middleware(app: FastAPI) -> None:
    # CORS — must be registered before other middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=settings.ALLOWED_METHODS,
        allow_headers=settings.ALLOWED_HEADERS,
    )

    # Reject requests from unexpected hosts in production
    if not settings.DEBUG:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["*"],  # Tighten to your domain in prod
        )

    # Request timing / logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "%s %s → %s  (%.1f ms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        # Expose timing in response header
        response.headers["X-Process-Time-Ms"] = f"{duration_ms:.1f}"
        return response


# ── Exception handlers ────────────────────────────────────────────────────────

def _register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """
        Pydantic v2 validation errors → structured 422 response.
        Strips internal Pydantic noise for cleaner client messages.
        """
        errors: list[dict[str, Any]] = []
        for error in exc.errors():
            loc = error.get("loc", [])
            # Drop the leading "body" segment for cleaner field paths
            field = ".".join(str(l) for l in loc if l != "body") or "request"
            errors.append(
                {
                    "field": field,
                    "message": error.get("msg", "Invalid value"),
                    "type": error.get("type", ""),
                }
            )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "VALIDATION_ERROR",
                "message": "Request validation failed. Check 'details' for field errors.",
                "details": errors,
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        """
        Normalise HTTPException detail into a consistent JSON envelope.
        Accepts both plain string details and dict details.
        """
        if isinstance(exc.detail, dict):
            content = {
                "error": exc.detail.get("code", "HTTP_ERROR"),
                "message": exc.detail.get("message", "An error occurred"),
                "details": exc.detail.get("details", None),
            }
        else:
            content = {
                "error": "HTTP_ERROR",
                "message": str(exc.detail),
                "details": None,
            }
        return JSONResponse(
            status_code=exc.status_code,
            content=content,
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """
        Catch-all for unexpected server errors.
        Logs the full traceback; returns a safe 500 to the client.
        """
        logger.exception(
            "Unhandled exception on %s %s", request.method, request.url.path
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Our team has been notified.",
                "details": None,
            },
        )


# ── Routers ───────────────────────────────────────────────────────────────────

def _register_routers(app: FastAPI) -> None:
    """
    Import and include all domain routers.
    Each router is responsible for its own prefix and tags.
    """
    # Lazy imports keep startup fast and avoid circular dependency issues
    from app.routers import auth, cart, categories, orders, products, users  # noqa: PLC0415

    app.include_router(auth.router,       prefix=settings.API_PREFIX)
    app.include_router(users.router,      prefix=settings.API_PREFIX)
    app.include_router(categories.router, prefix=settings.API_PREFIX)
    app.include_router(products.router,   prefix=settings.API_PREFIX)
    app.include_router(cart.router,       prefix=settings.API_PREFIX)
    app.include_router(orders.router,     prefix=settings.API_PREFIX)


# ── Health & meta endpoints ───────────────────────────────────────────────────

app = create_application()


@app.get(
    "/api/v1/health",
    tags=["Meta"],
    summary="Health check",
    response_description="Service health status",
)
async def health_check() -> dict:
    """
    Returns DB connectivity status and app metadata.
    Used by Render.com (and load balancers) to verify the service is alive.
    """
    db_healthy = await check_db_connection()
    return {
        "status": "healthy" if db_healthy else "degraded",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database": "connected" if db_healthy else "unreachable",
    }


@app.get("/", include_in_schema=False)
async def root() -> dict:
    """Redirect hint for the root path."""
    return {
        "message": f"Welcome to {settings.APP_NAME} v{settings.APP_VERSION}",
        "docs": f"{settings.API_PREFIX}/docs",
        "health": "/api/v1/health",
    }