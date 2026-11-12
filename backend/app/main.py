import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.health import router as health_router
from app.api.v1.identity import router as identity_router
from app.api.v1.authentication import router as authentication_router
from app.api.v1.data_scopes import router as data_scope_router
from app.api.v1.audit import router as audit_router
from app.application.exceptions import (
    EntityConflictError, EntityNotFoundError, InvalidOperationError,
)
from app.core.config import get_settings
from app.core.logging_config import configure_logging
from app.infrastructure.database import create_database_engine, create_session_factory

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger("biteguard.api")


@asynccontextmanager
async def lifespan(application: FastAPI):
    application.state.settings = settings
    application.state.database_engine = create_database_engine(settings)
    application.state.session_factory = (
        create_session_factory(application.state.database_engine)
        if application.state.database_engine is not None
        else None
    )
    logger.info("application_start environment=%s", settings.app_env)
    yield
    engine = getattr(application.state, "database_engine", None)
    application.state.session_factory = None
    if engine is not None:
        engine.dispose()
    logger.info("application_shutdown")


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="BiteGuard Platform API v1 with IAM user, role, and permission management.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Correlation-ID"],
)


@app.middleware("http")
async def correlation_and_request_logging(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    request.state.correlation_id = correlation_id
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.exception(
            "request_failed method=%s path=%s correlation_id=%s duration_ms=%s",
            request.method,
            request.url.path,
            correlation_id,
            elapsed_ms,
        )
        response = JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred.",
                    "correlation_id": correlation_id,
                }
            },
        )
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    logger.info(
        "request_completed method=%s path=%s status_code=%s "
        "correlation_id=%s duration_ms=%s",
        request.method,
        request.url.path,
        response.status_code,
        correlation_id,
        elapsed_ms,
    )
    response.headers["X-Correlation-ID"] = correlation_id
    return response


@app.exception_handler(EntityNotFoundError)
async def not_found_handler(request: Request, exc: EntityNotFoundError):
    return JSONResponse(status_code=404, content={"error": {"code": "NOT_FOUND", "message": str(exc)}})


@app.exception_handler(EntityConflictError)
async def conflict_handler(request: Request, exc: EntityConflictError):
    return JSONResponse(status_code=409, content={"error": {"code": "CONFLICT", "message": str(exc)}})


@app.exception_handler(InvalidOperationError)
async def invalid_operation_handler(request: Request, exc: InvalidOperationError):
    return JSONResponse(status_code=422, content={"error": {"code": "INVALID_OPERATION", "message": str(exc)}})


app.include_router(health_router, prefix=settings.api_v1_prefix)
app.include_router(identity_router, prefix=settings.api_v1_prefix)
app.include_router(authentication_router, prefix=settings.api_v1_prefix)
app.include_router(data_scope_router, prefix=settings.api_v1_prefix)
app.include_router(audit_router, prefix=settings.api_v1_prefix)


@app.get("/")
def root() -> dict[str, str]:
    return {"application": settings.app_name, "status": "running"}
