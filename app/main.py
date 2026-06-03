from contextlib import asynccontextmanager
from typing import Any, cast
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.responses import JSONResponse, Response
from sqlalchemy import text

from app.core.database import Database
from app.core.logging import get_logger, setup_logging
from app.core.redis import redis_client
from app.core.request_context import request_context_middleware
from app.di.container import Container
from app.errors.base import ApplicationError
from app.errors.handlers import (
    application_error_handler,
    http_exception_handler,
    request_validation_exception_handler,
    response_validation_exception_handler,
    unhandled_exception_handler,
)
from app.middleware import RateLimitMiddleware, user_context_middleware
from app.routers import api_router

setup_logging()
logger = get_logger(__name__)

container = Container()
db: Database = container.core.database()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Terminology Service")

    await db.create_extensions()

    try:
        await cast(Any, redis_client.ping())
        app.state.redis = redis_client
        logger.info("Connected to Redis successfully.")
    except Exception as e:
        logger.error("Failed to connect to Redis.", exc_info=e)
        app.state.redis = None
    yield

    logger.info("Shutting down Terminology Service...")
    await db.disconnect()
    logger.info("Database engine disposed.")


app: FastAPI = FastAPI(
    title="Terminology Service",
    version="1.0.0",
    description=(
        "FHIR Terminology microservice providing code system lookup, value set expansion, "
        "concept search, field binding validation, and cross-system concept mapping. "
        "Supports ICD-10-CM, LOINC, RxNorm, SNOMED CT, and FHIR R4 built-in code systems."
    ),
    lifespan=lifespan,
)

app.add_exception_handler(ApplicationError, application_error_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)
app.add_exception_handler(RequestValidationError, request_validation_exception_handler)
app.add_exception_handler(ResponseValidationError, response_validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)

app.container = container

app.add_middleware(RateLimitMiddleware)
app.middleware("http")(request_context_middleware)
app.middleware("http")(user_context_middleware)

app.include_router(api_router, prefix="/api/v1")


@app.get(
    "/health",
    operation_id="health_check",
    summary="Liveness probe",
    description="Returns 200 if the process is running. Does not check DB or Redis.",
    tags=["Health"],
)
async def health_check(request: Request):
    return JSONResponse(content={"status": "ok", "req_id": request.state.request_id})


@app.get(
    "/health/ready",
    operation_id="readiness_check",
    summary="Readiness probe",
    description="Returns 200 only when the database and Redis are reachable. Returns 503 if degraded.",
    tags=["Health"],
    responses={503: {"description": "One or more dependencies are unavailable"}},
)
async def readiness_check(request: Request):
    checks: dict[str, str] = {}
    healthy = True

    try:
        async with db.session() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        logger.error("Readiness: database check failed", exc_info=exc)
        checks["database"] = "unavailable"
        healthy = False

    redis = getattr(request.app.state, "redis", None)
    if redis is not None:
        try:
            await redis.ping()
            checks["redis"] = "ok"
        except Exception as exc:
            logger.error("Readiness: Redis check failed", exc_info=exc)
            checks["redis"] = "unavailable"
            healthy = False
    else:
        checks["redis"] = "unavailable"
        healthy = False

    payload = {
        "status": "ok" if healthy else "degraded",
        "req_id": request.state.request_id,
        "checks": checks,
    }
    return JSONResponse(content=payload, status_code=200 if healthy else 503)


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)
