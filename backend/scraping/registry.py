"""
Registry central de adapters.
Safe imports: un adapter roto no rompe todo el sistema.
"""

import logging
import importlib
from datetime import datetime
from zoneinfo import ZoneInfo

from scraping.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


def _load(module: str, cls: str):
    try:
        return getattr(importlib.import_module(module), cls)
    except Exception as e:
        logger.error(f"[registry] no se pudo cargar {cls} desde {module}: {e}")
        return None


# IMPORTANTE:
# Dejamos SOLO futbol para validar el pipeline real
# antes de volver a sumar el resto de los deportes.
_MAP = {
    "futbol": ("scraping.adapters.football", "FootballAdapter"),
}

ADAPTER_REGISTRY: dict[str, type[BaseScraper]] = {}

for sport, (mod, cls_name) in _MAP.items():
    cls = _load(mod, cls_name)
    if cls is not None:
        ADAPTER_REGISTRY[sport] = cls

logger.info(f"[registry] activos: {list(ADAPTER_REGISTRY.keys())}")


async def get_today_summary():
    all_matches = []
    by_sport = {}

    for sport, scraper_cls in ADAPTER_REGISTRY.items():
        try:
            scraper = scraper_cls()
            matches = await scraper.scrape()
            backend_matches = [m.to_backend_dict() for m in matches]

            by_sport[sport] = backend_matches
            all_matches.extend(backend_matches)

            logger.info(f"[{sport}] {len(backend_matches)} matches")
        except Exception as e:
            logger.exception(f"[{sport}] ERROR: {e}")
            by_sport[sport] = []

    live = [m for m in all_matches if m.get("status") == "live"]
    upcoming = [m for m in all_matches if m.get("status") == "upcoming"]
    finished = [m for m in all_matches if m.get("status") == "finished"]

    now_arg = datetime.now(ZoneInfo("America/Argentina/Buenos_Aires"))

    logger.info(f"[SUMMARY] total matches: {len(all_matches)}")
    logger.info(f"[SUMMARY] sports: { {k: len(v) for k, v in by_sport.items()} }")

    return {
        "date": now_arg.strftime("%Y-%m-%d"),
        "updated_at": now_arg.isoformat(),
        "matches": all_matches,
        "stats": {
            "live": len(live),
            "upcoming": len(upcoming),
            "finished": len(finished),
            "total": len(all_matches),
        },
        "by_sport": by_sport,
    }
