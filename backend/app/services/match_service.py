"""
Match service — fuente única de datos de partidos para el backend.
Orden de prioridad:
  1. Cache (si está vigente)
  2. Scrapers reales (scraping_bridge)
  3. Mock data (fallback si scrapers fallan)
"""
import logging
from app.models.match import Match
from app.cache import cache

logger = logging.getLogger(__name__)

STATUS_ORDER = {"live": 0, "upcoming": 1, "finished": 2}

# ---------------------------------------------------------------------------
# Mock data — fallback si scrapers no están disponibles
# ---------------------------------------------------------------------------
_MOCK: list[Match] = [
    Match(id="copa-arg-racing-sanmartin", sport="futbol", competition="Copa Argentina",
          home_team="Racing Club", away_team="San Martín de Formosa",
          home_score=1, away_score=1, status="live", minute="69'", start_time="21:15",
          argentina_relevance="club_arg", argentina_team="Racing Club", broadcast="TyC Sports"),
    Match(id="ln-basquet-ferro-instituto", sport="basquet", competition="Liga Nacional",
          home_team="Ferro", away_team="Instituto",
          home_score=54, away_score=61, status="live", minute="3er C",
          argentina_relevance="club_arg", broadcast="TyC Sports"),
    Match(id="atp-madrid-cerundolo", sport="tenis", competition="ATP Madrid · Masters 1000",
          home_team="Cerúndolo", away_team="Medvedev",
          status="live", minute="2do set",
          argentina_relevance="jugador_arg", argentina_team="Cerúndolo", broadcast="ESPN 3"),
    Match(id="libertadores-flamengo-lanus", sport="futbol", competition="Copa Libertadores",
          home_team="Flamengo", away_team="Lanús",
          status="upcoming", start_time="19:00",
          argentina_relevance="club_arg", argentina_team="Lanús", broadcast="ESPN"),
    Match(id="lpa-lanus-tigre", sport="futbol", competition="Liga Profesional Argentina",
          home_team="Lanús", away_team="Tigre",
          status="upcoming", start_time="21:30",
          argentina_relevance="club_arg", broadcast="TNT Sports"),
    Match(id="urba-casi-sic", sport="rugby", competition="TOP 14 URBA",
          home_team="CASI", away_team="SIC",
          status="upcoming", start_time="21:30",
          argentina_relevance="club_arg", broadcast="ESPN"),
    Match(id="lpa-river-cordoba", sport="futbol", competition="Liga Profesional Argentina",
          home_team="River Plate", away_team="Central Córdoba",
          home_score=2, away_score=0, status="finished", start_time="18:00",
          argentina_relevance="club_arg", broadcast="ESPN"),
    Match(id="copa-arg-huracan-platense", sport="futbol", competition="Copa Argentina",
          home_team="Huracán", away_team="Platense",
          home_score=1, away_score=1, status="finished", start_time="16:00",
          argentina_relevance="club_arg", broadcast="TyC Sports"),
]


def _sort(matches: list[Match]) -> list[Match]:
    return sorted(matches, key=lambda m: (STATUS_ORDER.get(m.status, 9), m.start_time or ""))


async def _get_from_cache_or_scrape(cache_key: str, scrape_fn) -> list[Match]:
    """Intenta cache → scrapers → mock."""
    cached = await cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        from app.scraping_bridge import fetch_today_from_scrapers
        results = await scrape_fn()
        if results:
            ttl = cache.ttl_for(cache_key.split(":")[0])
            await cache.set(cache_key, results, ttl=ttl)
            return results
    except Exception as e:
        logger.warning(f"[match_service] scrapers fallaron, usando mock: {e}")

    return _MOCK


# ---------------------------------------------------------------------------
# API pública del service
# ---------------------------------------------------------------------------

async def get_live_matches(sport: str | None = None) -> list[Match]:
    from app.scraping_bridge import fetch_live_from_scrapers
    key = f"live:{sport or 'all'}"
    matches = await _get_from_cache_or_scrape(
        key, lambda: fetch_live_from_scrapers(sports=[sport] if sport else None)
    )
    result = [m for m in matches if m.status == "live"]
    if sport:
        result = [m for m in result if m.sport == sport.lower()]
    return result


async def get_today_matches(sport: str | None = None) -> list[Match]:
    from app.scraping_bridge import fetch_today_from_scrapers
    key = f"today:{sport or 'all'}"
    matches = await _get_from_cache_or_scrape(
        key, lambda: fetch_today_from_scrapers(sports=[sport] if sport else None)
    )
    if sport:
        matches = [m for m in matches if m.sport == sport.lower()]
    return _sort(matches)


async def get_results_matches(sport: str | None = None) -> list[Match]:
    from app.scraping_bridge import fetch_results_from_scrapers
    key = f"results:{sport or 'all'}"
    matches = await _get_from_cache_or_scrape(
        key, lambda: fetch_results_from_scrapers(sports=[sport] if sport else None)
    )
    result = [m for m in matches if m.status == "finished"]
    if sport:
        result = [m for m in result if m.sport == sport.lower()]
    return _sort(result)


async def get_argentina_matches() -> list[Match]:
    key = "argentina:all"
    matches = await _get_from_cache_or_scrape(
        key, lambda: __import__("app.scraping_bridge", fromlist=["fetch_today_from_scrapers"]).fetch_today_from_scrapers()
    )
    arg = [m for m in matches if m.argentina_relevance != "none"]
    return _sort(arg)


async def get_club_matches(club_id: str) -> list[Match]:
    """Partidos de un club específico (para Club view)."""
    all_matches = await get_today_matches()
    club_lower = club_id.lower()
    return [
        m for m in all_matches
        if club_lower in (m.home_team or "").lower()
        or club_lower in (m.away_team or "").lower()
        or club_lower == (m.argentina_team or "").lower()
    ]
