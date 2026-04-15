"""
Health + debug endpoints.

Rutas:
- /api/health
- /api/health/full
- /api/health/scraping-quality
- /api/debug/scraping
- /api/debug/all
"""

import time
import logging
from collections import Counter, defaultdict
from typing import Any, Dict, List

from fastapi import APIRouter

from app.cache import cache

router = APIRouter()
logger = logging.getLogger(__name__)
DEBUG_TAG = "scrape-debug-v4-2026-04-15"


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


def _extract_cache_keys(cache_stats: Dict[str, Any]) -> List[str]:
    keys = cache_stats.get("keys") or []
    if isinstance(keys, list):
        return keys
    return []


def _group_keys(keys: List[str]) -> Dict[str, int]:
    grouped = defaultdict(int)
    for key in keys:
        if ":" in key:
            prefix = key.split(":", 1)[0]
        else:
            prefix = key
        grouped[prefix] += 1
    return dict(grouped)


def _extract_sport_from_key(key: str) -> str:
    lowered = key.lower()
    candidates = [
        "futbol",
        "tenis",
        "basquet",
        "rugby",
        "hockey",
        "voley",
        "handball",
        "futsal",
        "golf",
        "boxeo",
        "motorsport",
        "motogp",
        "polo",
        "esports",
        "dakar",
        "olimpicos",
    ]
    for sport in candidates:
        if sport in lowered:
            return sport
    if "today" in lowered or "hoy" in lowered:
        return "agenda"
    if "live" in lowered:
        return "live"
    return "otros"


def _safe_len(value: Any) -> int:
    try:
        return len(value)
    except Exception:
        return 0


@router.get("/health/scraping-quality")
async def scraping_quality():
    """
    Reporte liviano basado en cache/estado actual.
    No depende de scraping en vivo.
    """
    started = time.monotonic()
    cache_stats = await cache.stats()
    keys = _extract_cache_keys(cache_stats)
    last_valid_keys = cache_stats.get("last_valid_keys") or []

    sport_counter = Counter()
    for key in keys:
        sport_counter[_extract_sport_from_key(key)] += 1

    generic_competition_signals = 0
    missing_start_time_signals = 0

    # Señales blandas desde nombres de claves; no scraping en vivo
    for key in keys:
        lowered = key.lower()
        if "futbol" in lowered and ("today" in lowered or "hoy" in lowered):
            generic_competition_signals += 1
            missing_start_time_signals += 1

    return {
        "status": "ok",
        "timestamp": time.time(),
        "duration_ms": round((time.monotonic() - started) * 1000),
        "cache_backend": cache_stats.get("backend"),
        "active_keys": _safe_len(keys),
        "last_valid_keys_count": _safe_len(last_valid_keys),
        "groups": _group_keys(keys),
        "sports_present": dict(sport_counter),
        "coverage_signals": {
            "generic_competition_signal": generic_competition_signals,
            "missing_start_time_signal": missing_start_time_signals,
        },
        "notes": [
            "Reporte basado en cache y estado observable del backend.",
            "No ejecuta scraping en vivo.",
            "Sirve para visibilidad operativa básica.",
        ],
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
        from app.scraping_bridge import _SCRAPING_OK
        result["scraping_ok"] = _SCRAPING_OK
        if not _SCRAPING_OK:
            result["errors"].append("scraping package not importable")
            return result

        from scraping.registry import ADAPTER_REGISTRY, LOAD_ERRORS
        result["registry_load_errors"] = LOAD_ERRORS
        if sport not in ADAPTER_REGISTRY:
            result["errors"].append(
                f"'{sport}' no está en ADAPTER_REGISTRY. Disponibles: {list(ADAPTER_REGISTRY.keys())}"
            )
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
                "source": getattr(m, "source", None),
                "relevance": m.argentina_relevance,
                "start_time": getattr(m, "start_time_arg", None),
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
        from app.scraping_bridge import _SCRAPING_OK
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
                "sample": [
                    {"home": m.home_team, "away": m.away_team, "source": getattr(m, "source", None)}
                    for m in arg[:2]
                ],
            }
    except Exception as e:
        logger.error(f"[debug/all] {e}", exc_info=True)
        summary["error"] = str(e)

    return {
        "duration_ms": round((time.monotonic() - t0) * 1000),
        "sports": summary,
    }
