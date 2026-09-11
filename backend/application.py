"""Application factory: composition, resource lifecycle and HTTP policies."""

from contextlib import asynccontextmanager
import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from backend.observability import event, request_id
from backend.settings import ROOT, Settings


def create_app(settings=None, services_factory=None):
    settings = settings or Settings.from_environment()
    settings.configure_runtime()
    from backend.api import analysis, diagnostics, goals, recommendations
    from backend.services.container import Services

    factory = services_factory or Services

    @asynccontextmanager
    async def lifespan(app):
        resources = factory(settings)
        app.state.services = resources
        try:
            await resources.start()
            yield
        finally:
            await resources.close()

    app = FastAPI(
        title="AI Food Recognition API",
        description="Indian Food Recognition with Nutrition Analysis",
        version="1.0.0",
        lifespan=lifespan,
    )
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.state.settings = settings

    @limiter.limit(f"{settings.analysis_rate}/minute")
    async def limit_analysis(request: Request):
        return None

    @limiter.limit(f"{settings.recommendation_rate}/minute")
    async def limit_recommendations(request: Request):
        return None

    guards = {"/api/analyze-food": limit_analysis, "/api/recommendations": limit_recommendations}
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["Retry-After", "X-Request-ID"],
        max_age=3600,
    )

    @app.exception_handler(RateLimitExceeded)
    async def limited(request: Request, exc: RateLimitExceeded):
        return JSONResponse(
            status_code=429,
            content={
                "detail": "Too many requests. Please wait a minute and retry.",
                "error": "Rate limit exceeded",
                "message": "Too many requests. Please wait a minute and retry.",
                "retry_after": 60,
            },
            headers={"Retry-After": "60"},
        )

    @app.exception_handler(RequestValidationError)
    async def invalid(request: Request, exc: RequestValidationError):
        # Historical recommendation payload failures are 400; macro shape failures 422.
        code = 400 if request.url.path == "/api/recommendations" else 422
        if any(error["type"] == "value_error" for error in exc.errors()):
            code = 400
        return JSONResponse(
            status_code=code,
            content={
                "detail": "Invalid request. Check the supported goal, health context, food fields, and numeric limits."
            },
        )

    @app.middleware("http")
    async def operational_context(request: Request, call_next):
        token = request_id.set(uuid.uuid4().hex)
        started = time.monotonic()
        try:
            try:
                if request.method == "POST" and request.url.path in guards:
                    await guards[request.url.path](request)
                response = await call_next(request)
            except RateLimitExceeded as exc:
                response = await limited(request, exc)
            except Exception as exc:
                event("request_error", error_type=type(exc).__name__)
                response = JSONResponse(status_code=500, content={"detail": "Internal server error"})
            response.headers["X-Request-ID"] = request_id.get()
            if request.url.path.startswith("/api"):
                response.headers["Cache-Control"] = "no-store"
            route = request.scope.get("route")
            event(
                "request",
                method=request.method,
                route=getattr(route, "path", "unmatched"),
                status=response.status_code,
                duration_ms=round((time.monotonic() - started) * 1000, 2),
            )
            return response
        finally:
            request_id.reset(token)

    app.include_router(analysis.create_router(settings, limiter))
    app.include_router(recommendations.create_router(settings, limiter))
    app.include_router(goals.router)
    app.include_router(diagnostics.router)
    if settings.production or (ROOT / "web").is_dir():
        app.mount("/", StaticFiles(directory=str(ROOT / "web"), html=True, check_dir=False), name="frontend")
    # Provider SDK HTTP logs may include remote request details; use our allowlisted events.
    for name in (
        "httpx",
        "httpcore",
        "groq",
        "openai",
        "backend.services.nutrition_service",
        "backend.services.vision_service",
    ):
        logging.getLogger(name).setLevel(logging.CRITICAL)
    logging.getLogger("food.operations").setLevel(logging.INFO)
    return app
