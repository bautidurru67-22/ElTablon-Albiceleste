"""
registry.py — Orquestador central de scrapers para El Tablón Albiceleste

USO:
    from scrapers.registry import run_sport, run_all, get_today_summary
"""

import asyncio
import logging
from datetime import datetime
from .api_sports_base import today_art, now_art, cache_get, cache_set, TTL

from .football   import get_football_today
from .tennis     import get_tennis_today
from .basketball import get_basketball_today
from .rugby      import get_rugby_today
from .hockey     import get_hockey_today
from .volleyball import get_volleyball_today
from .futsal     import get_futsal_today

logger = logging.getLogger("tablon.registry")

# ─── ADAPTER REGISTRY ────────────────────────────────────────
ADAPTER_REGISTRY: dict[str, callable] = {
    "futbol":   get_football_today,
    "tenis":    get_tennis_today,
    "basquet":  get_basketball_today,
    "rugby":    get_rugby_today,
    "hockey":   get_hockey_today,
    "voley":    get_volleyball_today,
    "futsal":   get_futsal_today,
}

SPORT_LABELS = {
    "futbol":  "Fútbol",
    "tenis":   "Tenis",
    "basquet": "Básquet",
    "rugby":   "Rugby",
    "hockey":  "Hockey",
    "voley":   "Vóley",
    "futsal":  "Futsal",
}

# ─── RUN INDIVIDUAL ──────────────────────────────────────────
async def run_sport(sport: str, date: str | None = None) -> list[dict]:
    """Ejecuta el scraper de un deporte. Retorna [] si falla."""
    fn = ADAPTER_REGISTRY.get(sport)
    if fn is None:
        logger.error(f"[registry] Sport '{sport}' not in registry")
        return []
    try:
        result = await fn(date)
        return result or []
    except Exception as e:
        logger.error(f"[registry] {sport} failed: {e}")
        return []

# ─── RUN ALL ─────────────────────────────────────────────────
async def run_all(date: str | None = None) -> dict[str, list[dict]]:
    """Ejecuta todos los scrapers en paralelo."""
    d = date or today_art()
    tasks = {sport: run_sport(sport, d) for sport in ADAPTER_REGISTRY}
    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    output = {}
    for sport, result in zip(tasks.keys(), results):
        if isinstance(result, Exception):
            logger.error(f"[registry] {sport} exception: {result}")
            output[sport] = []
        else:
            output[sport] = result
    return output

# ─── GET TODAY SUMMARY (para /api/hoy) ───────────────────────
_RELEVANCE_ORDER = {"seleccion": 0, "club_arg": 1, "jugador_arg": 2, "none": 3}
_STATUS_ORDER    = {"live": 0, "upcoming": 1, "finished": 2}

async def get_today_summary(date: str | None = None) -> dict:
    """
    Retorna la estructura completa para /api/hoy:
    {
        date: "2026-04-12",
        updated_at: "...",
        stats: { live: N, upcoming: N, finished: N, total: N },
        matches: [ ...NormalizedMatch sorted... ],
        by_sport: { futbol: [...], tenis: [...], ... }
    }
    """
    d = date or today_art()
    cache_key = f"summary:{d}"

    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    logger.info(f"[registry] Building summary for {d}")

    all_results = await run_all(d)
    all_matches: list[dict] = []
    by_sport: dict[str, list[dict]] = {}

    for sport, matches in all_results.items():
        by_sport[sport] = matches
        all_matches.extend(matches)

    # Filter: only Argentina-relevant for the main feed
    arg_matches = [
        m for m in all_matches
        if m.get("argentina_relevance", "none") != "none"
    ]

    # Sort: live first, then by relevance, then by time
    sorted_matches = sorted(
        arg_matches,
        key=lambda m: (
            _STATUS_ORDER.get(m.get("status", "upcoming"), 9),
            _RELEVANCE_ORDER.get(m.get("argentina_relevance", "none"), 9),
            m.get("start_time", "99:99"),
        )
    )

    live_count     = sum(1 for m in arg_matches if m.get("status") == "live")
    upcoming_count = sum(1 for m in arg_matches if m.get("status") == "upcoming")
    finished_count = sum(1 for m in arg_matches if m.get("status") == "finished")

    summary = {
        "date": d,
        "updated_at": now_art().isoformat(),
        "stats": {
            "live":     live_count,
            "upcoming": upcoming_count,
            "finished": finished_count,
            "total":    len(arg_matches),
        },
        "matches": sorted_matches,
        "by_sport": by_sport,
    }

    # Cache: shorter TTL if there are live matches
    ttl = TTL["live"] if live_count > 0 else TTL["today"]
    cache_set(cache_key, summary, ttl)

    logger.info(
        f"[registry] {d}: {live_count} live, {upcoming_count} upcoming, "
        f"{finished_count} finished across {len([s for s in by_sport if by_sport[s]])} sports"
    )
    return summary
