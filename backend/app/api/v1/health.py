from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
def liveness() -> dict[str, str]:
    return {"status": "healthy", "check": "liveness"}


@router.get("/ready")
def readiness(request: Request) -> JSONResponse:
    settings = request.app.state.settings
    if not settings.database_is_configured:
        return JSONResponse(
            status_code=200,
            content={
                "status": "degraded",
                "check": "readiness",
                "dependencies": {"database": "not_configured"},
            },
        )
    engine = request.app.state.database_engine
    if engine is None:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "check": "readiness",
                "dependencies": {"database": "engine_unavailable"},
            },
        )
    try:
        from app.infrastructure.database import check_database_connection

        check_database_connection(engine)
    except Exception:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "check": "readiness",
                "dependencies": {"database": "unavailable"},
            },
        )
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "check": "readiness",
            "dependencies": {"database": "available"},
        },
    )
