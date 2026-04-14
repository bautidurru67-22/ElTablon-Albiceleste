"""
Health + debug endpoints.
/api/health        — siempre vivo
/api/health/full   — estado del sistema
/api/debug/scraping — test en vivo, todos los deportes
"""
import time
import logging
from fastapi import APIRouter
from app.cache import cache

router = APIRouter()
logger = logging.getLogger(__name__)
DEBUG_TAG = "scrape-debug-v3-2026-04-13"


@router.get("/health")
async def health():
    return {"status": "ok", "service": "tablon-albiceleste-api"}


@router.get("/health/full")
async def health_full():
    cache_stats = await cache.stats()
    keys = cache_stats.get("keys", [])
    lv_keys = cache_stats.get("last_valid_keys", [])
    return {
        "status": "ok",
        "timestamp": time.time(),
        "cache": {
            "backend": cache_stats.get("backend"),
            "active_keys": len(keys),
            "keys": keys,
            "last_valid_keys": lv_keys,
        },
    }


@router.get("/debug/scraping")
async def debug_scraping(sport: str = "futbol"):
    """
    Corre scraping EN VIVO para un deporte y muestra resultado.
    Parámetro: ?sport=futbol|tenis|basquet|rugby|hockey|voley|handball|futsal|golf|boxeo|motorsport|motogp
    """
    t0 = time.monotonic()
    result: dict = {
        "debug_tag": DEBUG_TAG,
        "sport": sport,
        "count": 0,
        "sample": [],
        "sources_tried": [],
        "errors": [],
        "duration_ms": 0,
    }

    try:
        from app.scraping_bridge import _SCRAPING_OK, _to_match
        result["scraping_ok"] = _SCRAPING_OK
        if not _SCRAPING_OK:
            result["errors"].append("scraping package not importable")
            return result

        from scraping.registry import ADAPTER_REGISTRY, LOAD_ERRORS
        result["registry_load_errors"] = LOAD_ERRORS
        if sport not in ADAPTER_REGISTRY:
            result["errors"].append(f"'{sport}' no está en ADAPTER_REGISTRY. Disponibles: {list(ADAPTER_REGISTRY.keys())}")
            return result
        adapter_cls = ADAPTER_REGISTRY[sport]
        result["sources_tried"] = getattr(adapter_cls, "SOURCE_ORDER", [])
        result["source_diagnostics"] = getattr(adapter_cls, "LAST_RUN", {})

        from scraping.orchestrator.coordinator import ScrapingCoordinator
        coord = ScrapingCoordinator({sport: ADAPTER_REGISTRY[sport]}, timeout_per_adapter=25)
        normalized = await coord.run_all_flat()
        arg = coord.get_argentina_matches(normalized)
        if sport != "futbol" and not arg:
            arg = normalized
            result["used_non_arg_fallback"] = True

        result["count"] = len(arg)
        result["total_before_filter"] = len(normalized)
        result["sample"] = [
            {
                "home": m.home_team,
                "away": m.away_team,
                "score": f"{m.home_score}-{m.away_score}" if m.home_score is not None else None,
                "status": m.status,
                "minute": m.minute,
                "competition": m.competition,
                "source": m.source,
                "relevance": m.argentina_relevance,
                "start_time": m.start_time_arg,
            }
            for m in arg[:10]
        ]
    except Exception as e:
        logger.error(f"[debug/scraping] {sport}: {e}", exc_info=True)
        result["errors"].append(str(e))

    result["duration_ms"] = round((time.monotonic() - t0) * 1000)
    return result


@router.get("/debug/all")
async def debug_all_sports():
    """Test rápido de todos los deportes activos. Muestra count por deporte."""
    from app.config import settings
    t0 = time.monotonic()
    summary = {}

    try:
        from app.scraping_bridge import _SCRAPING_OK, _to_match
        if not _SCRAPING_OK:
            return {"error": "scraping not importable"}

        from scraping.registry import ADAPTER_REGISTRY
        from scraping.orchestrator.coordinator import ScrapingCoordinator

        active = {s: ADAPTER_REGISTRY[s] for s in settings.active_sports if s in ADAPTER_REGISTRY}
        coord = ScrapingCoordinator(active, timeout_per_adapter=20)
        by_sport = await coord.run_all()

        for sp, matches in by_sport.items():
            arg = [m for m in matches if m.argentina_relevance != "none"]
            summary[sp] = {
                "total": len(matches),
                "argentina": len(arg),
                "sample": [{"home": m.home_team, "away": m.away_team, "source": m.source}
                           for m in arg[:2]],
            }
    except Exception as e:
        logger.error(f"[debug/all] {e}", exc_info=True)
        summary["error"] = str(e)

    return {
        "duration_ms": round((time.monotonic() - t0) * 1000),
        "sports": summary,
    }
