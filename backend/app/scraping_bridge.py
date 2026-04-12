"""
Bridge entre el backend FastAPI y el paquete scraping.

Resuelve el path al paquete scraping en cualquier entorno:
- Railway: WORKDIR=/app/backend, PYTHONPATH=/app/backend:/app
- Local:   tablon-albiceleste/backend/app/scraping_bridge.py
           tablon-albiceleste/scraping/ → parents[2]

ACTIVE_SPORTS son los deportes que se scrapean en cada ciclo.
"""
import sys
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _ensure_scraping_importable() -> bool:
    # 1) Intentar import directo (PYTHONPATH ya correcto)
    try:
        import scraping          # noqa
        import scraping.registry # noqa
        return True
    except ImportError:
        pass

    # 2) Agregar rutas manualmente como fallback
    bridge = Path(__file__).resolve()
    # bridge = .../backend/app/scraping_bridge.py
    # parents[2] = .../tablon-albiceleste/
    candidates = [
        bridge.parents[2],       # tablon-albiceleste/ (local)
        Path("/app"),            # Railway raíz
    ]
    for c in candidates:
        s = str(c)
        if c.exists() and s not in sys.path:
            sys.path.insert(0, s)

    try:
        import scraping          # noqa
        import scraping.registry # noqa
        logger.info("[bridge] scraping importado OK tras path fix")
        return True
    except ImportError as e:
        logger.error(
            f"[bridge] FALLO import scraping: {e} | sys.path={sys.path[:6]}"
        )
        return False


_SCRAPING_OK = _ensure_scraping_importable()

from app.models.match import Match

# Deportes con adapters reales activos
ACTIVE_SPORTS: list[str] = [
    "futbol",
    "tenis",
    "basquet",
    "rugby",
    "hockey",
    "voley",
    "handball",
    "futsal",
    "boxeo",
    "golf",
    "motorsport",
    "motogp",
]


async def fetch_live_from_scrapers(sports: list[str] | None = None) -> list[Match]:
    return await _run(sports=sports or ACTIVE_SPORTS, status_filter="live")


async def fetch_today_from_scrapers(sports: list[str] | None = None) -> list[Match]:
    return await _run(sports=sports or ACTIVE_SPORTS, status_filter=None)


async def fetch_results_from_scrapers(sports: list[str] | None = None) -> list[Match]:
    return await _run(sports=sports or ACTIVE_SPORTS, status_filter="finished")


async def _run(sports: list[str], status_filter: str | None) -> list[Match]:
    if not _SCRAPING_OK:
        logger.error("[bridge] scraping no disponible")
        return []

    try:
        from scraping.registry import ADAPTER_REGISTRY
        from scraping.orchestrator.coordinator import ScrapingCoordinator

        active = {k: v for k, v in ADAPTER_REGISTRY.items() if k in sports}
        logger.info(
            f"[bridge] start | sports={sports} filter={status_filter} "
            f"adapters={list(active.keys())}"
        )

        coordinator = ScrapingCoordinator(active, timeout_per_adapter=25)
        normalized = await coordinator.run_all_flat()
        logger.info(f"[bridge] run_all_flat → {len(normalized)} normalizados")

        arg = coordinator.get_argentina_matches(normalized)
        logger.info(f"[bridge] ARG relevance → {len(arg)}")

        if status_filter:
            before = len(arg)
            arg = [m for m in arg if m.status == status_filter]
            logger.info(f"[bridge] filtro '{status_filter}': {before}→{len(arg)}")

        result = [_to_match(m) for m in arg]
        logger.info(f"[bridge] entrega {len(result)} Match al backend")
        return result

    except ImportError as e:
        logger.error(f"[bridge] ImportError: {e}")
        return []
    except Exception as e:
        logger.error(f"[bridge] error: {e}", exc_info=True)
        return []


def _to_match(nm) -> Match:
    return Match(
        id=nm.id,
        sport=nm.sport,
        competition=nm.competition,
        home_team=nm.home_team,
        away_team=nm.away_team,
        home_score=nm.home_score,
        away_score=nm.away_score,
        status=nm.status,
        minute=nm.minute,
        datetime=nm.datetime_utc,
        start_time=nm.start_time_arg,
        argentina_relevance=nm.argentina_relevance,
        argentina_team=nm.argentina_team,
        broadcast=nm.broadcast,
    )
