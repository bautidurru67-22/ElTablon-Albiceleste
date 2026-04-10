import logging
import time
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from dotenv import load_dotenv

load_dotenv()

from app.config import settings

# ---------------------------------------------------------------------------
# Logging estructurado
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Iniciando El Tablón Albiceleste API — env={settings.environment}")

    # DB — crear tablas en dev, en prod usar Alembic
    if not settings.is_production:
        try:
            from app.db.session import create_tables
            import app.db.models  # noqa — registrar modelos
            await create_tables()
            logger.info("Tablas DB creadas/verificadas")
        except Exception as e:
            logger.warning(f"DB no disponible (usando mock): {e}")
    else:
        logger.info("Producción: usar 'alembic upgrade head' para migraciones")

    # Scheduler
    from app.scheduler import setup_scheduler
    sched = setup_scheduler()
    sched.start()
    logger.info("Scheduler activo: live/45s · today/5min · results/10min")

    # Pre-calentar cache
    from app.scheduler import _job_today
    try:
        await _job_today()
        logger.info("Cache pre-calentado")
    except Exception as e:
        logger.warning(f"Pre-warm falló — sirviendo mock: {e}")

    yield

    sched.shutdown(wait=False)
    logger.info("Shutdown completo")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="El Tablón Albiceleste API",
    description="Datos deportivos argentinos en tiempo real",
    version="0.3.0",
    lifespan=lifespan,
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None,
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Middleware — request logging + timing
# ---------------------------------------------------------------------------
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    duration_ms = round((time.monotonic() - start) * 1000)
    if request.url.path not in ("/api/health", "/api/health/full"):
        logger.info(
            f"{request.method} {request.url.path} → {response.status_code} [{duration_ms}ms]"
        )
    return response


# ---------------------------------------------------------------------------
# Error handlers globales
# ---------------------------------------------------------------------------
@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "validation_error", "detail": exc.errors()},
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    logger.error(f"Error no manejado en {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "internal_error", "detail": "Error interno del servidor"},
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
from app.api.routes import router
app.include_router(router, prefix="/api")

logger.info(f"CORS: {settings.allowed_origins}")
