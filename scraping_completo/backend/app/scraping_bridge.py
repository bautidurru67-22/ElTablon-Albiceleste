"""
Bridge entre FastAPI y el paquete scraping.
Resuelve imports en Railway (PYTHONPATH=/app/backend:/app) y local.
"""
import sys
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _ensure_scraping_importable() -> bool:
    try:
        import scraping          # noqa
        import scraping.registry # noqa
        return True
    except ImportError:
        pass

    bridge = Path(__file__).resolve()
    for candidate in [bridge.parents[2], Path("/app")]:
        s = str(candidate)
        if candidate.exists() and s not in sys.path:
            sys.path.insert(0, s)

    try:
        import scraping          # noqa
        import scraping.registry # noqa
        logger.info("[bridge] scraping importado OK (path fix)")
        return True
    except ImportError as e:
        logger.error(f"[bridge] FALLO import scraping: {e}")
        return False


_SCRAPING_OK = _ensure_scraping_importable()

from app.models.match import Match


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
        datetime=getattr(nm, "datetime_utc", None),
        start_time=getattr(nm, "start_time_arg", None),
        argentina_relevance=nm.argentina_relevance,
        argentina_team=nm.argentina_team,
        broadcast=nm.broadcast,
    )
