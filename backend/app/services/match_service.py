"""
Match service — SOLO LEE CACHE. Nunca scrapea en request.
Si cache vacío → get_last_valid → [] como último recurso.
"""
import logging
from app.models.match import Match
from app.cache import cache

logger = logging.getLogger(__name__)

STATUS_ORDER = {"live": 0, "upcoming": 1, "finished": 2}

# Señales de contenido argentino (rápidas/robustas)
ARG_KEYWORDS = [
    "argentina", "liga profesional", "primera nacional", "copa argentina",
    "reserva", "femenina", "federal a", "federal b", "primera c",
    "promocional amateur", "libertadores", "sudamericana",
    "afa", "selección argentina", "superliga argentina",
]

# Señales a excluir (para evitar ruido de países no deseados en /hoy y /deporte)
EXCLUDE_KEYWORDS = [
    "chile", "chilean", "copa chile", "primera división de chile",
    "union la calera", "deportes concepcion", "colo colo", "universidad de chile",
]

TOP_LEAGUE_KEYWORDS = [
    "premier league", "la liga", "serie a", "bundesliga", "ligue 1", "champions league"
]


def _norm(s: str | None) -> str:
    return (s or "").strip().lower()


def _haystack(m: Match) -> str:
    return " ".join([
        _norm(getattr(m, "competition", "")),
        _norm(getattr(m, "home_team", "")),
        _norm(getattr(m, "away_team", "")),
        _norm(getattr(m, "argentina_team", "")),
    ])


def _is_argentina_match(m: Match) -> bool:
    # Si el pipeline ya marcó relevancia argentina, respetar
    if getattr(m, "argentina_relevance", "none") != "none":
        return True

    hay = _haystack(m)
    return any(k in hay for k in ARG_KEYWORDS)


def _is_excluded_match(m: Match) -> bool:
    hay = " ".join([
        _norm(getattr(m, "competition", "")),
        _norm(getattr(m, "home_team", "")),
        _norm(getattr(m, "away_team", "")),
    ])
    return any(k in hay for k in EXCLUDE_KEYWORDS)


def _relevance_score(m: Match) -> int:
    """
    Reglas editoriales (más alto = más importante):
    - Selección Argentina > clubes argentinos > copas/ligas argentinas > argentinos en ligas top > resto.
    """
    score = 10
    hay = _haystack(m)
    sport = _norm(getattr(m, "sport", ""))
    argentina_relevance = _norm(getattr(m, "argentina_relevance", "none"))

    if argentina_relevance == "seleccion":
        score += 120
    elif argentina_relevance == "club_arg":
        score += 95
    elif argentina_relevance == "jugador_arg":
        score += 70

    if sport == "futbol":
        score += 40

    if "selección argentina" in hay:
        score += 90

    if "liga profesional" in hay or "copa argentina" in hay:
        score += 80

    if "libertadores" in hay or "sudamericana" in hay:
        score += 75

    if any(k in hay for k in TOP_LEAGUE_KEYWORDS) and _is_argentina_match(m):
        score += 60

    if _norm(getattr(m, "status", "")) == "live":
        score += 15

    if getattr(m, "argentina_team", None):
        score += 12

    return score


def _sort(matches: list) -> list:
    return sorted(
        matches,
        key=lambda m: (
            STATUS_ORDER.get(m.status, 9),
            -_relevance_score(m),
            m.start_time or "99:99"
        )
    )


def _clean(matches: list[Match]) -> list[Match]:
    # 1) excluye ruido explícito
    filtered = [m for m in matches if not _is_excluded_match(m)]
    # 2) prioriza relevancia argentina si existe señal (evita cross-country noise)
    arg = [m for m in filtered if _is_argentina_match(m)]
    return arg if arg else filtered


async def _read_cache(key: str) -> list[Match]:
    """Lee cache → last_valid → []. NUNCA scrapea."""
    data = await cache.get(key)
    if data is not None:
        return data
    data = await cache.get_last_valid(key)
    if data is not None:
        logger.debug(f"[match_service] {key}: usando last_valid")
        return data
    return []


# ── Endpoints públicos ──────────────────────────────────────────────────────

async def get_hoy() -> dict:
    """Agenda completa del día — lee hoy:all del agregador."""
    matches: list[Match] = await _read_cache("hoy:all")
    matches = _clean(matches)

    live = [m for m in matches if m.status == "live"]
    upcoming = [m for m in matches if m.status == "upcoming"]
    finished = [m for m in matches if m.status == "finished"]
    return {
        "en_vivo": _sort(live),
        "proximos": _sort(upcoming),
        "finalizados": _sort(finished),
        "total": len(matches),
    }


async def get_futbol_hoy() -> list[Match]:
    return _sort(_clean(await _read_cache("today:futbol")))


async def get_futbol_live() -> list[Match]:
    data = _clean(await _read_cache("live:futbol"))
    return [m for m in data if m.status == "live"]


async def get_tenis_hoy() -> list[Match]:
    return _sort(_clean(await _read_cache("today:tenis")))


async def get_basquet_hoy() -> list[Match]:
    return _sort(_clean(await _read_cache("today:basquet")))


async def get_rugby_hoy() -> list[Match]:
    return _sort(_clean(await _read_cache("today:rugby")))


async def get_hockey_hoy() -> list[Match]:
    return _sort(_clean(await _read_cache("today:hockey")))


async def get_sport_hoy(sport: str) -> list[Match]:
    return _sort(_clean(await _read_cache(f"today:{sport}")) )


# ── Compat con rutas viejas /api/matches/* ──────────────────────────────────

async def get_live_matches(sport: str | None = None) -> list[Match]:
    if sport:
        data = _clean(await _read_cache(f"live:{sport}"))
        return [m for m in data if m.status == "live"]
    data = _clean(await _read_cache("live:futbol"))
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
    # ya está limpio + ordenado por get_hoy, pero lo reforzamos:
    return _sort([m for m in all_m if _is_argentina_match(m)])


async def get_club_matches(club_id: str) -> list[Match]:
    all_m = await get_today_matches()
    q = club_id.lower().replace("-", " ")
    return [
        m for m in all_m
        if q in (m.home_team or "").lower()
        or q in (m.away_team or "").lower()
        or q == (m.argentina_team or "").lower()
    ]
