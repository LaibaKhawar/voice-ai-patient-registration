"""FastAPI application: REST API, Vapi webhook and the static dashboard."""

import logging
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.admin import auth_router, calls_router, health_router, stats_router
from app.api.patients import router as patients_router
from app.config import get_settings
from app.envelope import APIError, fail
from app.logging_utils import configure_logging
from app.voice.webhook import router as vapi_router

configure_logging()
log = logging.getLogger("app")

# Built Next.js static export (see Dockerfile). Optional in local dev.
DASHBOARD_DIR = Path(__file__).resolve().parent.parent / "dashboard_build"


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Voice AI Patient Registration API",
        version="1.0.0",
        description=(
            "Patient registration REST API backing a Vapi voice agent. Patient and call endpoints "
            "require `Authorization: Bearer <API_KEY>`. All responses use the envelope "
            '`{"data": ..., "error": null}`.'
        ),
    )

    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE"],
            allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-API-Key"],
        )

    @app.middleware("http")
    async def access_log_and_headers(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        if not request.url.path.startswith("/dashboard"):
            response.headers["Cache-Control"] = "no-store"
        # Query strings are omitted: they can contain PII (phone, DOB filters).
        log.info("http", extra={"fields": {
            "method": request.method, "path": request.url.path, "status": response.status_code,
            "ms": round((time.perf_counter() - start) * 1000, 1),
        }})
        return response

    @app.exception_handler(APIError)
    async def handle_api_error(_: Request, exc: APIError):
        return fail(exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def handle_validation(_: Request, exc: RequestValidationError):
        errors = exc.errors()
        if any(e.get("type") == "json_invalid" for e in errors):
            return fail(400, "INVALID_JSON", "Request body is not valid JSON.")
        if all(e.get("loc", [None])[0] in ("query", "path", "header") for e in errors):
            details = [{"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]} for e in errors]
            return fail(400, "INVALID_REQUEST", "Invalid request parameters.", details)
        details = [
            {
                "field": ".".join(str(p) for p in e["loc"] if p != "body") or "body",
                # Strip pydantic's "Value error, " prefix; never echo the rejected input back.
                "message": e["msg"].removeprefix("Value error, "),
            }
            for e in errors
        ]
        return fail(422, "VALIDATION_ERROR", "One or more fields are invalid.", details)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http(_: Request, exc: StarletteHTTPException):
        code = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}.get(exc.status_code, "HTTP_ERROR")
        return fail(exc.status_code, code, str(exc.detail))

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception):
        log.exception("unhandled_error", extra={"fields": {"path": request.url.path}})
        return fail(500, "INTERNAL_ERROR", "An unexpected error occurred.")

    for router in (health_router, auth_router, patients_router, calls_router, stats_router, vapi_router):
        app.include_router(router)

    if DASHBOARD_DIR.is_dir():
        app.mount("/dashboard", StaticFiles(directory=DASHBOARD_DIR, html=True), name="dashboard")

        @app.get("/", include_in_schema=False)
        def root():
            return RedirectResponse("/dashboard/")

        @app.get("/favicon.ico", include_in_schema=False)
        def favicon():
            icon = DASHBOARD_DIR / "favicon.ico"
            return FileResponse(icon) if icon.exists() else RedirectResponse("/dashboard/")
    else:
        @app.get("/", include_in_schema=False)
        def root_no_dashboard():
            return RedirectResponse("/docs")

    return app


app = create_app()
