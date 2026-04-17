import asyncio
import logging
import os
from importlib import import_module

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.startup.scraper_runner import start_scraping_loop

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="El Tablón Albiceleste API",
    version="1.0.0",
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


def _include_router_if_exists(
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


# ─────────────────────────────────────────────────────────────────────────────
# Rutas
# ─────────────────────────────────────────────────────────────────────────────

# Ruta principal que ya sabemos que existe
_include_router_if_exists("app.api.hoy", prefix="/api/hoy", tags=["Hoy"])

# Intentos opcionales para no romper si el repo usa otra organización
_include_router_if_exists("app.api.matches", prefix="/api/matches", tags=["Matches"])
_include_router_if_exists("app.api.auth", prefix="/api/auth", tags=["Auth"])
_include_router_if_exists("app.api.routes.hoy", prefix="/api/hoy", tags=["Hoy"])
_include_router_if_exists("app.api.routes.matches", prefix="/api/matches", tags=["Matches"])


# ─────────────────────────────────────────────────────────────────────────────
# Startup
# ─────────────────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event() -> None:
    logger.info("[main] startup iniciado")
    asyncio.create_task(start_scraping_loop())
    logger.info("[main] scraper loop lanzado")


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
    return JSONResponse(
        {
            "ok": True,
            "status": "healthy",
        }
    )
