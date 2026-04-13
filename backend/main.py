"""
main.py — El Tablón Albiceleste API
Reglas: startup nunca bloquea, / y /api/health siempre vivos,
scraping solo por scheduler, cache protege requests.
"""
import logging
import time
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from dotenv import load_dotenv

load_dotenv()

from app.config import settings

logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"[startup] El Tablón Albiceleste — env={settings.environment}")

    # ── Scheduler (no bloquea startup) ─────────────────────────────────────
    sched = None
    try:
        from app.scheduler import build_scheduler
        sched = build_scheduler()
        sched.start()
        logger.info("[startup] scheduler activo")
    except Exception as e:
        logger.error(f"[startup] scheduler falló (API sigue viva): {e}")

    # ── Prewarm NO BLOQUEANTE — dispara job en background después de 5s ────
    # Así el healthcheck pasa inmediatamente y el primer dato llega en ~10s
    if settings.scraping_enabled:
        async def _delayed_prewarm():
            await asyncio.sleep(5)
            try:
                from app.scheduler import job_futbol_hoy, job_hoy_agregador
                logger.info("[startup] prewarm background iniciando")
                await job_futbol_hoy()
                await job_hoy_agregador()
                logger.info("[startup] prewarm background completo")
            except Exception as e:
                logger.warning(f"[startup] prewarm background falló: {e}")
        asyncio.create_task(_delayed_prewarm())

    yield  # ← API lista, healthcheck pasa desde aquí

    if sched:
        sched.shutdown(wait=False)
    logger.info("[shutdown] completo")


app = FastAPI(
    title="El Tablón Albiceleste API",
    version="0.4.0",
    lifespan=lifespan,
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    ms = round((time.monotonic() - start) * 1000)
    path = request.url.path
    if path not in ("/api/health", "/"):
        logger.info(f"{request.method} {path} → {response.status_code} [{ms}ms]")
    return response


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "validation_error", "detail": exc.errors()},
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    logger.error(f"[error] {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "internal_error"},
    )


# ── Raíz siempre viva ───────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {"service": "tablon-albiceleste-api", "status": "ok", "version": "0.4.0"}


# ── Rutas /api ──────────────────────────────────────────────────────────────
from app.api.routes import router
app.include_router(router, prefix="/api")

logger.info(f"[startup] CORS: {settings.allowed_origins}")
