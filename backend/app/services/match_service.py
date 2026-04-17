"""
Match service — LEE CACHE y recompone la agenda si hoy:all está vacío o incompleto.
Nunca scrapea en request.
"""

from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from app.models.match import Match
from app.cache import cache

logger = logging.getLogger(__name__)

STATUS_ORDER = {"live": 0, "upcoming": 1, "finished": 2}

SPORT_CACHE_KEYS = [
    "today:futbol",
    "today:tenis",
    "today:basquet",
    "today:rugby",
    "today:hockey",
    "today:voley",
    "today:futsal",
    "today:handball",
    "today:boxeo",
    "today:golf",
    "today:polo",
    "today:motorsport",
    "today:motogp",
    "today:esports",
]

ARG_KEYWORDS = [
    "argentina",
    "liga profesional",
    "liga profesional de futbol",
    "liga profesional de fútbol",
    "primera nacional",
    "primera b",
    "primera c",
    "copa argentina",
    "reserva",
    "femenina",
    "federal a",
    "federal b",
    "promocional amateur",
    "libertadores",
    "sudamericana",
    "afa",
    "selección argentina",
    "seleccion argentina",
    "superliga argentina",
]

EXCLUDE_KEYWORDS = [
    "chile",
    "chilean",
    "copa chile",
    "primera división de chile",
    "union la calera",
    "deportes concepcion",
    "colo colo",
    "universidad de chile",
]

TOP_LEAGUE_KEYWORDS = [
    "premier league",
    "la liga",
    "serie a",
    "bundesliga",
    "ligue 1",
    "champions league",
]


def _norm(s: str | None) -> str:
    return (s or "").strip().lower()


def _haystack(m: Match) -> str:
    return " ".join(
        [
            _norm(getattr(m, "competition", "")),
            _norm(getattr(m, "home_team", "")),
            _norm(getattr(m, "away_team", "")),
            _norm(getattr(m, "argentina_team", "")),
            _norm(getattr(m, "argentina_relevance", "")),
        ]
    )


def _match_identity(m: Match) -> str:
    return "|".join(
        [
            _norm(getattr(m, "sport", "")),
            _norm(getattr(m, "competition", "")),
            _norm(getattr(m, "home_team", "")),
            _norm(getattr(m, "away_team", "")),
            _norm(getattr(m, "start_time", "")),
            _norm(getattr(m, "status", "")),
        ]
    )


def _is_argentina_match(m: Match) -> bool:
    if _norm(getattr(m, "argentina_relevance", "none")) != "none":
        return True

    hay = _haystack(m)
    return any(k in hay for k in ARG_KEYWORDS)


def _is_excluded_match(m: Match) -> bool:
    hay = " ".join(
        [
            _norm(getattr(m, "competition", "")),
            _norm(getattr(m, "home_team", "")),
            _norm(getattr(m, "away_team", "")),
        ]
    )
    return any(k in hay for k in EXCLUDE_KEYWORDS)


def _is_session_event(m: Match) -> bool:
    hay = " ".join(
        [
            _norm(getattr(m, "sport", "")),
            _norm(getattr(m, "competition", "")),
            _norm(getattr(m, "home_team", "")),
            _norm(getattr(m, "away_team", "")),
        ]
    )
    keywords = [
        "practice",
        "práctica",
        "fp1",
        "fp2",
        "fp3",
        "training",
        "entrenamiento",
        "session",
        "qualy",
        "clasificacion",
        "clasificación",
        "sprint",
    ]
    return any(k in hay for k in keywords)


def _relevance_score(m: Match) -> int:
    score = 10
    hay = _haystack(m)
    sport = _norm(getattr(m, "sport", ""))
    argentina_relevance = _norm(getattr(m, "argentina_relevance", "none"))
    status = _norm(getattr(m, "status", ""))

    if argentina_relevance == "seleccion":
        score += 140
    elif argentina_relevance == "club_arg":
        score += 100
    elif argentina_relevance == "jugador_arg":
        score += 60

    if sport == "futbol":
        score += 50
    elif sport == "basquet":
        score += 20
    elif sport == "tenis":
        score += 16
    elif sport == "rugby":
        score += 14
    elif sport == "hockey":
        score += 14
    elif sport == "voley":
        score += 12
    elif sport in {"motorsport", "motogp"}:
        score -= 20

    if "selección argentina" in hay or "seleccion argentina" in hay:
        score += 100

    if "argentina u17" in hay or "argentina u20" in hay or "argentina u23" in hay:
        score += 60

    if "liga profesional" in hay:
        score += 90

    if "primera nacional" in hay or "primera b" in hay or "primera c" in hay:
        score += 55

    if "copa argentina" in hay:
        score += 75

    if "libertadores" in hay or "sudamericana" in hay:
        score += 70

    if any(k in hay for k in TOP_LEAGUE_KEYWORDS) and _is_argentina_match(m):
        score += 50

    if status == "live":
        score += 30
    elif status == "upcoming":
        score += 10
    elif status == "finished":
        score -= 5

    if getattr(m, "argentina_team", None):
        score += 12

    if _is_session_event(m):
        score -= 40

    return score


def _sort(matches: list[Match]) -> list[Match]:
    return sorted(
        matches,
        key=lambda m: (
            STATUS_ORDER.get(_norm(getattr(m, "status", "")), 9),
            -_relevance_score(m),
            _norm(getattr(m, "start_time", "99:99")) or "99:99",
            _norm(getattr(m, "competition", "")),
        ),
    )


def _dedupe(matches: list[Match]) -> list[Match]:
    seen: set[str] = set()
    out: list[Match] = []
    for m in matches:
        key = _match_identity(m)
        if key in seen:
            continue
        seen.add(key)
        out.append(m)
    return out


def _clean(matches: list[Match]) -> list[Match]:
    filtered = [m for m in matches if not _is_excluded_match(m)]
    arg = [m for m in filtered if _is_argentina_match(m)]
    cleaned = arg if arg else filtered
    return _dedupe(cleaned)


def _to_dict(m: Match) -> dict:
    return {
        "id": getattr(m, "id", None),
        "sport": getattr(m, "sport", None),
        "competition": getattr(m, "competition", None),
        "home_team": getattr(m, "home_team", None),
        "away_team": getattr(m, "away_team", None),
        "home_score": getattr(m, "home_score", None),
        "away_score": getattr(m, "away_score", None),
        "status": getattr(m, "status", None),
        "minute": getattr(m, "minute", None),
        "start_time": getattr(m, "start_time", None),
        "tv": getattr(m, "broadcast", None),
        "broadcast": getattr(m, "broadcast", None),
        "argentina_relevance": getattr(m, "argentina_relevance", "none"),
        "argentina_team": getattr(m, "argentina_team", None),
    }


def _group_sections(matches: list[Match]) -> list[dict]:
    seleccion = [
        m for m in matches if _norm(getattr(m, "argentina_relevance", "")) == "seleccion"
    ]
    ligas = [
        m
        for m in matches
        if _norm(getattr(m, "argentina_relevance", "")) == "club_arg"
    ]
    exterior = [
        m
        for m in matches
        if _norm(getattr(m, "argentina_relevance", "")) == "jugador_arg"
        and _norm(getattr(m, "sport", "")) not in {"motorsport", "motogp"}
    ]
    motorsport = [
        m
        for m in matches
        if _norm(getattr(m, "sport", "")) in {"motorsport", "motogp"}
    ]

    sections = []

    if seleccion:
        sections.append(
            {
                "key": "selecciones",
                "title": "Selecciones nacionales",
                "items": [_to_dict(m) for m in _sort(seleccion)],
            }
        )

    if ligas:
        sections.append(
            {
                "key": "ligas_locales",
                "title": "Ligas locales",
                "items": [_to_dict(m) for m in _sort(ligas)],
            }
        )

    if exterior:
        sections.append(
            {
                "key": "argentinos_exterior",
                "title": "Argentinos en el exterior",
                "items": [_to_dict(m) for m in _sort(exterior)],
            }
        )

    if motorsport:
        sections.append(
            {
                "key": "motorsport",
                "title": "Motorsport argentino",
                "items": [_to_dict(m) for m in _sort(motorsport)],
            }
        )

    return sections


async def _read_cache(key: str) -> list[Match]:
    data = await cache.get(key)
    if data is not None:
        return data
    data = await cache.get_last_valid(key)
    if data is not None:
        logger.debug(f"[match_service] {key}: usando last_valid")
        return data
    return []


async def _read_all_today_sources() -> list[Match]:
    all_matches: list[Match] = []
    for key in SPORT_CACHE_KEYS:
        try:
            data = await _read_cache(key)
            if data:
                all_matches.extend(data)
        except Exception as e:
            logger.warning(f"[match_service] error leyendo {key}: {e}")
    return _dedupe(all_matches)


async def _read_best_hoy_matches() -> list[Match]:
    hoy_all = await _read_cache("hoy:all")
    hoy_all = _clean(hoy_all)

    by_sport = {}
    for m in hoy_all:
        sport = _norm(getattr(m, "sport", ""))
        by_sport[sport] = by_sport.get(sport, 0) + 1

    # Si hoy:all está bien poblado, usarlo.
    # Si viene vacío o dominado por un solo deporte, reconstruir desde caches por deporte.
    if len(hoy_all) >= 5 and len(by_sport) >= 2:
        logger.info(f"[match_service] usando hoy:all ({len(hoy_all)} matches, sports={by_sport})")
        return _sort(hoy_all)

    fallback = await _read_all_today_sources()
    fallback = _clean(fallback)

    if fallback:
        fb_sports = {}
        for m in fallback:
            sport = _norm(getattr(m, "sport", ""))
            fb_sports[sport] = fb_sports.get(sport, 0) + 1
        logger.info(
            f"[match_service] hoy:all insuficiente ({len(hoy_all)}). "
            f"Usando fallback por deporte ({len(fallback)} matches, sports={fb_sports})"
        )
        return _sort(fallback)

    logger.info(f"[match_service] sin data en hoy:all ni fallback por deporte")
    return _sort(hoy_all)


async def get_hoy() -> dict:
    """
    Agenda completa del día.
    Devuelve formato rico para frontend:
    {
      ok,
      date,
      data: {
        date,
        updated_at,
        matches,
        stats,
        summary,
        by_sport,
        sections,
        load_errors
      }
    }
    """
    matches = await _read_best_hoy_matches()

    live = [m for m in matches if _norm(getattr(m, "status", "")) == "live"]
    upcoming = [m for m in matches if _norm(getattr(m, "status", "")) == "upcoming"]
    finished = [m for m in matches if _norm(getattr(m, "status", "")) == "finished"]

    by_sport: dict[str, int] = {}
    for m in matches:
        sport = _norm(getattr(m, "sport", "")) or "otro"
        by_sport[sport] = by_sport.get(sport, 0) + 1

    now_arg = datetime.now(ZoneInfo("America/Argentina/Buenos_Aires"))
    today_str = now_arg.date().isoformat()

    return {
        "ok": True,
        "date": today_str,
        "data": {
            "date": today_str,
            "updated_at": now_arg.isoformat(),
            "matches": [_to_dict(m) for m in matches],
            "stats": {
                "live": len(live),
                "upcoming": len(upcoming),
                "finished": len(finished),
                "total": len(matches),
            },
            "summary": {
                "live": len(live),
                "upcoming": len(upcoming),
                "finished": len(finished),
                "total": len(matches),
            },
            "by_sport": by_sport,
            "sections": _group_sections(matches),
            "load_errors": {},
        },
    }


async def get_futbol_hoy() -> list[Match]:
    return _sort(_clean(await _read_cache("today:futbol")))


async def get_futbol_live() -> list[Match]:
    data = _clean(await _read_cache("live:futbol"))
    return [m for m in data if _norm(getattr(m, "status", "")) == "live"]


async def get_tenis_hoy() -> list[Match]:
    return _sort(_clean(await _read_cache("today:tenis")))


async def get_basquet_hoy() -> list[Match]:
    return _sort(_clean(await _read_cache("today:basquet")))


async def get_rugby_hoy() -> list[Match]:
    return _sort(_clean(await _read_cache("today:rugby")))


async def get_hockey_hoy() -> list[Match]:
    return _sort(_clean(await _read_cache("today:hockey")))


async def get_sport_hoy(sport: str) -> list[Match]:
    return _sort(_clean(await _read_cache(f"today:{sport}")))


async def get_live_matches(sport: str | None = None) -> list[Match]:
    if sport:
        data = _clean(await _read_cache(f"live:{sport}"))
        return [m for m in data if _norm(getattr(m, "status", "")) == "live"]
    data = _clean(await _read_cache("live:futbol"))
    return [m for m in data if _norm(getattr(m, "status", "")) == "live"]


async def get_today_matches(sport: str | None = None) -> list[Match]:
    if sport:
        return await get_sport_hoy(sport)
    hoy = await get_hoy()
    raw = hoy["data"]["matches"]
    # compat: devolvemos dicts o Match según cómo los consuma el backend.
    return raw


async def get_results_matches(sport: str | None = None) -> list[Match]:
    matches = await get_today_matches(sport)
    if matches and isinstance(matches[0], dict):
        return [m for m in matches if _norm(m.get("status")) == "finished"]
    return [m for m in matches if _norm(getattr(m, "status", "")) == "finished"]


async def get_argentina_matches() -> list[Match]:
    hoy = await get_hoy()
    all_m = hoy["data"]["matches"]
    return [
        m for m in all_m
        if _norm(m.get("argentina_relevance", "none")) != "none"
    ]


async def get_club_matches(club_id: str) -> list[Match]:
    all_m = await get_today_matches()
    q = club_id.lower().replace("-", " ")
    if all_m and isinstance(all_m[0], dict):
        return [
            m for m in all_m
            if q in _norm(m.get("home_team"))
            or q in _norm(m.get("away_team"))
            or q == _norm(m.get("argentina_team"))
        ]
    return [
        m for m in all_m
        if q in _norm(getattr(m, "home_team", ""))
        or q in _norm(getattr(m, "away_team", ""))
        or q == _norm(getattr(m, "argentina_team", ""))
    ]
