import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.core.config import settings
from app.core.errors import AppError
from app.core.middleware import RequestLoggingMiddleware

_CORS_SEGMENT_GITHUB_IO = r"https://[a-zA-Z0-9-]+\.github\.io"
# Development: browsers send Origin like http://192.168.x.x:3000 for LAN Next dev servers.
_CORS_SEGMENT_DEV_HTTP = r"http://[0-9a-zA-Z.-]+:[0-9]+"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    from pathlib import Path

    from alembic import command
    from alembic.config import Config

    Path("data").mkdir(parents=True, exist_ok=True)

    if settings.run_migrations_on_startup:
        alembic_ini = Path(__file__).resolve().parents[1] / "alembic.ini"
        cfg = Config(str(alembic_ini))
        cfg.set_main_option("sqlalchemy.url", settings.database_url)
        command.upgrade(cfg, "head")

    from app.services.jobs.job_scheduler import shutdown_scheduler, start_scheduler

    if settings.enable_job_scheduler:
        start_scheduler()
    try:
        yield
    finally:
        if settings.enable_job_scheduler:
            shutdown_scheduler()


logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(levelname)s %(name)s %(message)s",
)

FASTAPI_DESCRIPTION = """\
MVP: paste resume and job description as plain text; file upload is not supported.

Match endpoint SLO (stub implementation): aim for p99 under ~1–2s. Heavier AI workloads may move to async jobs later.
"""

app = FastAPI(
    title="Resume Job Dashboard — AI",
    version="0.1.0",
    description=FASTAPI_DESCRIPTION,
    lifespan=lifespan,
)

_allow_origin_regex = (
    rf"({_CORS_SEGMENT_GITHUB_IO}|{_CORS_SEGMENT_DEV_HTTP})$"
    if settings.app_env == "development"
    else rf"{_CORS_SEGMENT_GITHUB_IO}$"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    # GitHub Pages + LAN http dev (when APP_ENV=development).
    allow_origin_regex=_allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)

app.include_router(router, prefix="/api")


@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(RequestValidationError)
async def validation_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    first = errors[0] if errors else {}
    loc = first.get("loc", ())
    msg = first.get("msg", "Validation error")
    loc_suffix = f" {'/'.join(str(x) for x in loc)}" if loc else ""
    message = f"{msg}{loc_suffix}"
    body = {"error": {"code": "VALIDATION_ERROR", "message": message}}
    return JSONResponse(status_code=400, content=body)


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail and "message" in detail:
        code = str(detail["code"])
        message = str(detail["message"])
    elif isinstance(detail, str):
        code = "HTTP_ERROR"
        message = detail
    else:
        code = "HTTP_ERROR"
        message = str(detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": code, "message": message}},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    logging.getLogger(__name__).exception("Unhandled error")
    message = str(exc) if settings.debug else "An unexpected error occurred"
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR", "message": message}},
    )
