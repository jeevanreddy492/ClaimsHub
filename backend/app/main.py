"""ClaimsHub API entry point: app factory, middleware, error handlers, health checks."""

import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, OperationalError
from starlette.responses import Response

from app import __version__
from app.api.v1.routes import router as v1_router
from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.logging import correlation_id_var, setup_logging, user_var
from app.domain.exceptions import DomainError
from app.repositories.base import oracle_error_code, translate_db_error

log = logging.getLogger("claimshub.api")


def _error(status: int, code: str, message: str, details: list | None = None) -> JSONResponse:
    body: dict[str, Any] = {
        "code": code,
        "message": message,
        "correlation_id": correlation_id_var.get(),
    }
    if details:
        body["details"] = details
    return JSONResponse(status_code=status, content=body)


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging(settings.log_level)

    app = FastAPI(
        title="ClaimsHub API",
        version=__version__,
        description="Claims management for Short-Term Disability, Life insurance and "
        "employee leave. All data is fake.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Correlation-ID"],
    )

    @app.middleware("http")
    async def correlation_and_access_log(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        cid = request.headers.get("X-Correlation-ID") or uuid.uuid4().hex
        correlation_id_var.set(cid[:64])
        user_var.set("-")
        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 1)
            level = logging.WARNING if status_code >= 500 or duration_ms > 1000 else logging.INFO
            log.log(
                level,
                "request",
                extra={
                    "event": "http_request",
                    "method": request.method,
                    "path": request.url.path,
                    "route": getattr(request.scope.get("route"), "path", request.url.path),
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                    "client_ip": request.client.host if request.client else None,
                    "user": getattr(request.state, "username", "-"),
                },
            )
        response.headers["X-Correlation-ID"] = correlation_id_var.get()
        return response

    @app.exception_handler(DomainError)
    async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
        log.info(
            "domain_error",
            extra={"event": "domain_error", "error_code": exc.code, "error_message": exc.message},
        )
        return _error(exc.status_code, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"field": ".".join(str(p) for p in e["loc"][1:]), "message": e["msg"]}
            for e in exc.errors()
        ]
        return _error(422, "VALIDATION_FAILED", "Request data is not valid", details)

    @app.exception_handler(DBAPIError)
    async def db_error_handler(_: Request, exc: DBAPIError) -> JSONResponse:
        mapped = translate_db_error(exc)
        if mapped:
            return _error(mapped.status_code, mapped.code, mapped.message)
        log.error(
            "database_error",
            exc_info=exc,
            extra={"event": "database_error", "ora_code": oracle_error_code(exc)},
        )
        if isinstance(exc, OperationalError):
            return _error(503, "DATABASE_UNAVAILABLE", "Database is not reachable right now")
        return _error(500, "DATABASE_ERROR", "Unexpected database error")

    @app.exception_handler(Exception)
    async def unhandled_handler(_: Request, exc: Exception) -> JSONResponse:
        log.error("unhandled_error", exc_info=exc, extra={"event": "unhandled_error"})
        return _error(
            500,
            "INTERNAL_ERROR",
            "Something went wrong. Use the correlation_id to find the details in the logs.",
        )

    @app.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        """Liveness: the process is up."""
        return {"status": "ok", "version": __version__}

    @app.get("/health/ready", tags=["health"])
    def ready() -> JSONResponse:
        """Readiness: the database answers."""
        started = time.perf_counter()
        try:
            with SessionLocal() as s:
                dialect = s.get_bind().dialect.name
                s.execute(text("SELECT 1 FROM dual" if dialect == "oracle" else "SELECT 1"))
            db_ms = round((time.perf_counter() - started) * 1000, 1)
            return JSONResponse({"status": "ok", "database": "up", "db_ms": db_ms})
        except Exception as exc:
            log.error("readiness_failed", exc_info=exc, extra={"event": "readiness_failed"})
            return JSONResponse({"status": "degraded", "database": "down"}, status_code=503)

    app.include_router(v1_router)
    return app


app = create_app()
