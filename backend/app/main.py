import logging
import os
from contextlib import asynccontextmanager
from importlib import import_module

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.scheduler import build_scheduler

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)

logger = logging.getLogger(__name__)


def _include_router_if_exists(
    app: FastAPI,
    module_path: str,
    *,
    router_name: str = "router",
    prefix: str = "",
    tags: list[str] | None = None,
) -> bool:
    try:
        module = import_module(module_path)
        router = getattr(module, router_name, None)
        if router is None:
            logger.warning(f"[main] {module_path} no expone '{router_name}'")
            return False

        app.include_router(router, prefix=prefix, tags=tags or [])
        logger.info(f"[main] router incluido: {module_path} prefix={prefix}")
        return True
    except Exception as e:
        logger.warning(f"[main] no se pudo incluir {module_path}: {e}")
        return False


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("[main] startup iniciado")

    scheduler = None
    try:
        scheduler = build_scheduler()
        scheduler.start()
        app.state.scheduler = scheduler
        logger.info("[main] scheduler iniciado")
    except Exception as e:
        logger.error(f"[main] no se pudo iniciar scheduler: {e}", exc_info=True)
        app.state.scheduler = None

    yield

    logger.info("[main] shutdown iniciado")
    try:
        scheduler = getattr(app.state, "scheduler", None)
        if scheduler:
            scheduler.shutdown(wait=False)
            logger.info("[main] scheduler detenido")
    except Exception as e:
        logger.warning(f"[main] error al detener scheduler: {e}")


app = FastAPI(
    title="El Tablón Albiceleste API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://eltablon-albiceleste.vercel.app",
        "https://el-tablon-albiceleste.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────────
# Rutas
# ─────────────────────────────────────────────────────────────────────────────

# Ruta principal del backend nuevo
_include_router_if_exists(app, "backend.api_hoy", tags=["Hoy"])

# Compatibilidad con estructuras alternativas del repo
_include_router_if_exists(app, "app.api.hoy", prefix="/api/hoy", tags=["Hoy"])
_include_router_if_exists(app, "app.api.matches", prefix="/api/matches", tags=["Matches"])
_include_router_if_exists(app, "app.api.auth", prefix="/api/auth", tags=["Auth"])
_include_router_if_exists(app, "app.api.routes.hoy", prefix="/api/hoy", tags=["Hoy"])
_include_router_if_exists(app, "app.api.routes.matches", prefix="/api/matches", tags=["Matches"])

# ─────────────────────────────────────────────────────────────────────────────
# Healthchecks
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "ok": True,
        "service": "El Tablón Albiceleste API",
        "version": "1.0.0",
    }


@app.get("/health")
async def health():
    scheduler = getattr(app.state, "scheduler", None)
    return JSONResponse(
        {
            "ok": True,
            "status": "healthy",
            "scheduler_running": bool(scheduler and getattr(scheduler, "running", False)),
        }
    )
