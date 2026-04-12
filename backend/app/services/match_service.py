"""
Match service — pipeline cache → scrapers → [].
Sin mocks. Sin datos inventados.
"""
import logging
from app.models.match import Match
from app.cache import cache

logger = logging.getLogger(__name__)

STATUS_ORDER = {"live": 0, "upcoming": 1, "finished": 2}


def _sort(matches: list[Match]) -> list[Match]:
    return sorted(
        matches,
        key=lambda m: (STATUS_ORDER.get(m.status, 9), m.start_time or "")
    )


async def _fetch(cache_key: str, scrape_fn) -> list[Match]:
    cached = await cache.get(cache_key)
    if cached is not None:
        logger.debug(f"[match_service] hit {cache_key}: {len(cached)}")
        return cached

    logger.info(f"[match_service] miss {cache_key} — scraping")
    try:
        results = await scrape_fn()
        ttl = cache.ttl_for(cache_key.split(":")[0])
        if results:
            await cache.set(cache_key, results, ttl=ttl)
        logger.info(f"[match_service] {cache_key} → {len(results)} (ttl={ttl}s)")
        return results
    except Exception as e:
        logger.error(f"[match_service] {cache_key} scraping error: {e}", exc_info=True)
        return []


async def get_live_matches(sport: str | None = None) -> list[Match]:
    from app.scraping_bridge import fetch_live_from_scrapers
    key = f"live:{sport or 'all'}"
    matches = await _fetch(key, lambda: fetch_live_from_scrapers(
        sports=[sport] if sport else None
    ))
    result = [m for m in matches if m.status == "live"]
    if sport:
        result = [m for m in result if m.sport == sport]
    return result


async def get_today_matches(sport: str | None = None) -> list[Match]:
    from app.scraping_bridge import fetch_today_from_scrapers
    key = f"today:{sport or 'all'}"
    matches = await _fetch(key, lambda: fetch_today_from_scrapers(
        sports=[sport] if sport else None
    ))
    if sport:
        matches = [m for m in matches if m.sport == sport]
    return _sort(matches)


async def get_results_matches(sport: str | None = None) -> list[Match]:
    from app.scraping_bridge import fetch_results_from_scrapers
    key = f"results:{sport or 'all'}"
    matches = await _fetch(key, lambda: fetch_results_from_scrapers(
        sports=[sport] if sport else None
    ))
    result = [m for m in matches if m.status == "finished"]
    if sport:
        result = [m for m in result if m.sport == sport]
    return _sort(result)


async def get_argentina_matches() -> list[Match]:
    from app.scraping_bridge import fetch_today_from_scrapers
    key = "argentina:all"
    matches = await _fetch(key, fetch_today_from_scrapers)
    return _sort([m for m in matches if m.argentina_relevance != "none"])


async def get_club_matches(club_id: str) -> list[Match]:
    all_m = await get_today_matches()
    q = club_id.lower().replace("-", " ")
    return [
        m for m in all_m
        if q in (m.home_team or "").lower()
        or q in (m.away_team or "").lower()
        or q == (m.argentina_team or "").lower()
    ]
