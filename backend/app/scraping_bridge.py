"""
Bridge entre el backend FastAPI y el paquete scraping.
Ejecuta los adapters reales y convierte NormalizedMatch → Match (modelo backend).
Deportes activos en tiempo real: football, tennis, basketball, rugby, hockey.
"""
import sys
import os
import logging
from pathlib import Path

# Asegurar que el paquete scraping sea importable desde el backend
_ROOT = Path(__file__).resolve().parents[3]  # raíz del proyecto
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.models.match import Match

logger = logging.getLogger(__name__)

# Deportes con scraping real activo
ACTIVE_SPORTS: list[str] = [
    "futbol",
    "tenis",
    "basquet",
    "rugby",
    "hockey",
]


async def fetch_live_from_scrapers(sports: list[str] | None = None) -> list[Match]:
    """Ejecuta scrapers y retorna partidos en vivo como modelos Match."""
    return await _run(sports=sports or ACTIVE_SPORTS, status_filter="live")


async def fetch_today_from_scrapers(sports: list[str] | None = None) -> list[Match]:
    """Ejecuta scrapers y retorna todos los partidos del día."""
    return await _run(sports=sports or ACTIVE_SPORTS, status_filter=None)


async def fetch_results_from_scrapers(sports: list[str] | None = None) -> list[Match]:
    """Ejecuta scrapers y retorna solo partidos finalizados."""
    return await _run(sports=sports or ACTIVE_SPORTS, status_filter="finished")


async def _run(
    sports: list[str],
    status_filter: str | None,
) -> list[Match]:
    try:
        from scraping.registry import ADAPTER_REGISTRY
        from scraping.orchestrator.coordinator import ScrapingCoordinator

        active_adapters = {k: v for k, v in ADAPTER_REGISTRY.items() if k in sports}
        coordinator = ScrapingCoordinator(active_adapters, timeout_per_adapter=25)
        normalized = await coordinator.run_all_flat()
        arg_matches = coordinator.get_argentina_matches(normalized)

        if status_filter:
            arg_matches = [m for m in arg_matches if m.status == status_filter]

        return [_to_match(m) for m in arg_matches]

    except Exception as e:
        logger.error(f"[scraping_bridge] error ejecutando scrapers: {e}")
        return []


def _to_match(nm) -> Match:
    """Convierte NormalizedMatch → Match (modelo Pydantic del backend)."""
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
