"""
Match service — SOLO LEE CACHE. Nunca scrapea en request.
Si cache vacío → get_last_valid → [] como último recurso.
"""
import logging
from app.models.match import Match
from app.cache import cache

logger = logging.getLogger(__name__)

STATUS_ORDER = {"live": 0, "upcoming": 1, "finished": 2}


def _sort(matches: list) -> list:
    return sorted(
        matches,
        key=lambda m: (STATUS_ORDER.get(m.status, 9), m.start_time or "")
    )


async def _read_cache(key: str) -> list[Match]:
    """Lee cache → last_valid → warmup puntual → []."""
    data = await cache.get(key)
    if data is not None:
        return data
    data = await cache.get_last_valid(key)
    if data is not None:
        logger.debug(f"[match_service] {key}: usando last_valid")
        return data
    await _warm_cache_for_key(key)
    data = await cache.get(key)
    if data is not None:
        logger.info(f"[match_service] {key}: warmup on-demand OK ({len(data)})")
        return data
    return []


async def _warm_cache_for_key(key: str) -> None:
    """
    Si scheduler no precalentó cache (cold start/restart), intenta un warmup puntual.
    Evita dejar frontend vacío cuando hay datos disponibles en fuentes.
    """
    try:
        from app.scheduler import _run_sport, job_hoy_agregador
        from app.config import settings

        if key.startswith("today:"):
            sport = key.split(":", 1)[1]
            results = await _run_sport(sport)
            if results:
                await cache.set(key, results, ttl=settings.cache_ttl_today, source=f"ondemand/{sport}")
            return

        if key.startswith("live:"):
            sport = key.split(":", 1)[1]
            results = await _run_sport(sport, status_filter="live")
            if results:
                await cache.set(key, results, ttl=settings.cache_ttl_live, source=f"ondemand/{sport}/live")
            return

        if key == "hoy:all":
            # Asegura mínimos deportes core antes de agregar
            for sport in ("futbol", "tenis", "basquet", "rugby", "hockey"):
                skey = f"today:{sport}"
                if await cache.get(skey) is None:
                    res = await _run_sport(sport)
                    if res:
                        await cache.set(skey, res, ttl=settings.cache_ttl_today, source=f"ondemand/{sport}")
            await job_hoy_agregador()
    except Exception as e:
        logger.warning(f"[match_service] warmup on-demand falló para {key}: {e}")


# ── Endpoints públicos ──────────────────────────────────────────────────────

async def get_hoy() -> dict:
    """Agenda completa del día — lee hoy:all del agregador."""
    matches: list[Match] = await _read_cache("hoy:all")
    live      = [m for m in matches if m.status == "live"]
    upcoming  = [m for m in matches if m.status == "upcoming"]
    finished  = [m for m in matches if m.status == "finished"]
    return {
        "en_vivo":    _sort(live),
        "proximos":   _sort(upcoming),
        "finalizados": _sort(finished),
        "total":      len(matches),
    }


async def get_futbol_hoy() -> list[Match]:
    return _sort(await _read_cache("today:futbol"))


async def get_futbol_live() -> list[Match]:
    data = await _read_cache("live:futbol")
    return [m for m in data if m.status == "live"]


async def get_tenis_hoy() -> list[Match]:
    return _sort(await _read_cache("today:tenis"))


async def get_basquet_hoy() -> list[Match]:
    return _sort(await _read_cache("today:basquet"))


async def get_rugby_hoy() -> list[Match]:
    return _sort(await _read_cache("today:rugby"))


async def get_hockey_hoy() -> list[Match]:
    return _sort(await _read_cache("today:hockey"))


async def get_sport_hoy(sport: str) -> list[Match]:
    return _sort(await _read_cache(f"today:{sport}"))


# ── Compat con rutas viejas /api/matches/* ──────────────────────────────────

async def get_live_matches(sport: str | None = None) -> list[Match]:
    if sport:
        data = await _read_cache(f"live:{sport}")
        return [m for m in data if m.status == "live"]
    data = await _read_cache("live:futbol")
    return [m for m in data if m.status == "live"]


async def get_today_matches(sport: str | None = None) -> list[Match]:
    if sport:
        return await get_sport_hoy(sport)
    hoy = await get_hoy()
    return _sort(hoy["en_vivo"] + hoy["proximos"] + hoy["finalizados"])


async def get_results_matches(sport: str | None = None) -> list[Match]:
    matches = await get_today_matches(sport)
    return [m for m in matches if m.status == "finished"]


async def get_argentina_matches() -> list[Match]:
    hoy = await get_hoy()
    all_m = hoy["en_vivo"] + hoy["proximos"] + hoy["finalizados"]
    return _sort([m for m in all_m if getattr(m, "argentina_relevance", "none") != "none"])


async def get_club_matches(club_id: str) -> list[Match]:
    all_m = await get_today_matches()
    q = club_id.lower().replace("-", " ")
    return [
        m for m in all_m
        if q in (m.home_team or "").lower()
        or q in (m.away_team or "").lower()
        or q == (m.argentina_team or "").lower()
    ]
