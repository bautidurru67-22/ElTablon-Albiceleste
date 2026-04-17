"""
api_hoy.py — Endpoints agregados para El Tablón Albiceleste

Reglas:
- SIEMPRE usa ART (UTC-3)
- /hoy, /resultados, /live y /calendario leen cache central (hoy:all + today:*)
- Nunca bloquea request con scraping sincrónico
- Ranking editorial fino y extensible:
    1) Selección Argentina
    2) Clubes argentinos top / torneos top
    3) Ligas locales y copas argentinas
    4) Copas CONMEBOL
    5) Argentinos en el exterior
    6) Otros deportes relevantes
    7) Motorsport argentino
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from api_sports_base import now_art, today_art
from app.cache import cache
from app.config import settings
from app.models.match import Match

router = APIRouter(tags=["hoy"])


# ─────────────────────────────────────────────────────────────────────────────
# Config editorial
# ─────────────────────────────────────────────────────────────────────────────

BIG_ARG_CLUBS = {
    "boca",
    "boca juniors",
    "river",
    "river plate",
    "racing",
    "racing club",
    "independiente",
    "san lorenzo",
    "san lorenzo de almagro",
    "rosario central",
    "newells",
    "newell's old boys",
    "newells old boys",
    "velez",
    "velez sarsfield",
    "estudiantes",
    "estudiantes de la plata",
    "huracan",
    "huracán",
    "lanus",
    "lanús",
    "talleres",
}

MID_ARG_CLUBS = {
    "union",
    "unión",
    "union de santa fe",
    "belgrano",
    "instituto",
    "platense",
    "banfield",
    "argentinos juniors",
    "defensa y justicia",
    "godoy cruz",
    "tigre",
    "sarmiento",
    "central cordoba",
    "central córdoba",
    "barracas central",
    "aldosivi",
    "quilmes",
    "chacarita",
    "ferro",
    "all boys",
    "nueva chicago",
    "patronato",
    "temperley",
    "almirante brown",
    "excursionistas",
    "arsenal sarandi",
    "arsenal de sarandi",
    "arsenal de sarandí",
}

LOCAL_TOP_COMPETITIONS = {
    "liga profesional",
    "liga profesional de futbol",
    "liga profesional de fútbol",
    "torneo betano",
    "copa argentina",
    "primera nacional",
}

LOCAL_MID_COMPETITIONS = {
    "primera b",
    "b metro",
    "primera c",
    "primera d",
    "federal a",
    "federal b",
    "regional amateur",
    "reserva",
    "femenina",
}

CONMEBOL_COMPETITIONS = {
    "libertadores",
    "sudamericana",
    "recopa",
    "conmebol",
}

EXTERIOR_TOP_COMPETITIONS = {
    "premier league",
    "la liga",
    "serie a",
    "bundesliga",
    "ligue 1",
    "champions league",
    "europa league",
    "conference league",
}

MOTORSPORT_SESSION_TOKENS = {
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
}

GENERIC_COMPETITION_VALUES = {
    "",
    "futbol",
    "fútbol",
    "football",
    "soccer",
    "tenis",
    "tennis",
    "basquet",
    "básquet",
    "basketball",
    "rugby",
    "hockey",
    "voley",
    "vóley",
    "volleyball",
    "handball",
    "futsal",
    "golf",
    "boxeo",
    "boxing",
    "motorsport",
    "motogp",
    "polo",
    "esports",
}


# ─────────────────────────────────────────────────────────────────────────────
# Helpers base
# ─────────────────────────────────────────────────────────────────────────────

def _to_dict(m: Match | dict[str, Any]) -> dict[str, Any]:
    if isinstance(m, Match):
        d = m.model_dump()
    else:
        d = dict(m)

    if d.get("tv") is None and d.get("broadcast"):
        d["tv"] = d.get("broadcast")

    return d


def _norm_text(v: Any) -> str:
    return str(v or "").strip().lower()


def _combined_text(match: dict[str, Any]) -> str:
    return " ".join(
        [
            _norm_text(match.get("competition")),
            _norm_text(match.get("home_team")),
            _norm_text(match.get("away_team")),
            _norm_text(match.get("argentina_team")),
            _norm_text(match.get("category")),
            _norm_text(match.get("sport")),
        ]
    )


def _contains_any(text: str, tokens: set[str]) -> bool:
    return any(token in text for token in tokens)


def _status_order(match: dict[str, Any]) -> int:
    status = _norm_text(match.get("status"))
    return {"live": 0, "upcoming": 1, "finished": 2}.get(status, 9)


def _parse_start_time(value: Any) -> str:
    text = str(value or "").strip()
    return text if text else "99:99"


def _has_valid_start_time(match: dict[str, Any]) -> bool:
    start = _norm_text(match.get("start_time"))
    return bool(start and start not in {"null", "none", "a confirmar", "tbd"})


# ─────────────────────────────────────────────────────────────────────────────
# Clasificación editorial
# ─────────────────────────────────────────────────────────────────────────────

def _is_argentina_selection(match: dict[str, Any]) -> bool:
    hay = _combined_text(match)
    return (
        _norm_text(match.get("argentina_relevance")) == "seleccion"
        or "seleccion argentina" in hay
        or "selección argentina" in hay
        or "argentina u17" in hay
        or "argentina u20" in hay
        or "argentina u23" in hay
        or (
            "argentina" in hay
            and (
                "sub 17" in hay
                or "sub-17" in hay
                or "sub 20" in hay
                or "sub-20" in hay
                or "sub 23" in hay
                or "sub-23" in hay
                or "u17" in hay
                or "u20" in hay
                or "u23" in hay
            )
        )
    )


def _is_local_league(match: dict[str, Any]) -> bool:
    comp = _norm_text(match.get("competition"))

    if _norm_text(match.get("argentina_relevance")) == "club_arg":
        return True

    return _contains_any(comp, LOCAL_TOP_COMPETITIONS | LOCAL_MID_COMPETITIONS)


def _is_local_top_competition(match: dict[str, Any]) -> bool:
    return _contains_any(_norm_text(match.get("competition")), LOCAL_TOP_COMPETITIONS)


def _is_local_mid_competition(match: dict[str, Any]) -> bool:
    return _contains_any(_norm_text(match.get("competition")), LOCAL_MID_COMPETITIONS)


def _is_conmebol(match: dict[str, Any]) -> bool:
    return _contains_any(_norm_text(match.get("competition")), CONMEBOL_COMPETITIONS)


def _is_top_exterior(match: dict[str, Any]) -> bool:
    return _contains_any(_norm_text(match.get("competition")), EXTERIOR_TOP_COMPETITIONS)


def _is_motorsport(match: dict[str, Any]) -> bool:
    return _norm_text(match.get("sport")) in {"motorsport", "motogp", "dakar"}


def _is_session_event(match: dict[str, Any]) -> bool:
    return _contains_any(_combined_text(match), MOTORSPORT_SESSION_TOKENS)


def _is_generic_competition(match: dict[str, Any]) -> bool:
    return _norm_text(match.get("competition")) in GENERIC_COMPETITION_VALUES


def _is_exterior(match: dict[str, Any]) -> bool:
    return (
        _norm_text(match.get("argentina_relevance")) == "jugador_arg"
        and not _is_motorsport(match)
    )


def _sport_weight(match: dict[str, Any]) -> int:
    sport = _norm_text(match.get("sport"))

    if sport == "futbol":
        return 240
    if sport == "basquet":
        return 140
    if sport == "tenis":
        return 120
    if sport == "rugby":
        return 110
    if sport == "hockey":
        return 110
    if sport == "voley":
        return 95
    if sport == "handball":
        return 90
    if sport == "futsal":
        return 85
    if sport == "boxeo":
        return 75
    if sport == "golf":
        return 60
    if _is_motorsport(match):
        return 40
    return 50


def _club_name_weight(name: str) -> int:
    n = _norm_text(name)

    if any(token in n for token in BIG_ARG_CLUBS):
        return 230

    if any(token in n for token in MID_ARG_CLUBS):
        return 120

    return 0


def _teams_weight(match: dict[str, Any]) -> int:
    return _club_name_weight(match.get("home_team")) + _club_name_weight(match.get("away_team"))


def _competition_weight(match: dict[str, Any]) -> int:
    if _is_local_top_competition(match):
        return 420

    if _is_local_mid_competition(match):
        return 220

    if _is_conmebol(match):
        return 360

    if _is_top_exterior(match):
        return 120

    return 0


def _status_weight(match: dict[str, Any]) -> int:
    status = _norm_text(match.get("status"))

    if status == "live":
        return 420
    if status == "upcoming":
        return 180
    if status == "finished":
        return 40
    return 0


def _relevance_weight(match: dict[str, Any]) -> int:
    relevance = _norm_text(match.get("argentina_relevance"))

    if relevance == "seleccion":
        return 1500
    if relevance == "club_arg":
        return 820
    if relevance == "jugador_arg":
        return 420
    return 0


def _selection_weight(match: dict[str, Any]) -> int:
    if not _is_argentina_selection(match):
        return 0

    hay = _combined_text(match)

    if "mayor" in hay:
        return 900
    if "u23" in hay or "sub 23" in hay or "sub-23" in hay:
        return 700
    if "u20" in hay or "sub 20" in hay or "sub-20" in hay:
        return 650
    if "u17" in hay or "sub 17" in hay or "sub-17" in hay:
        return 620

    return 800


def _quality_penalty(match: dict[str, Any]) -> int:
    hay = _combined_text(match)
    penalty = 0

    if _is_motorsport(match):
        penalty += 140

    if _is_session_event(match):
        penalty += 320

    if " ii" in f" {hay}" or " reserva" in f" {hay}" or " filial" in hay:
        penalty += 220

    if "amistoso" in hay or "friendly" in hay:
        penalty += 170

    if _is_generic_competition(match):
        penalty += 220

    if not _has_valid_start_time(match):
        penalty += 70

    return penalty


def _editorial_score(match: dict[str, Any]) -> int:
    score = 0

    score += _relevance_weight(match)
    score += _selection_weight(match)
    score += _sport_weight(match)
    score += _competition_weight(match)
    score += _teams_weight(match)
    score += _status_weight(match)

    if _norm_text(match.get("argentina_team")):
        score += 50

    if _is_exterior(match) and _is_top_exterior(match):
        score += 80

    score -= _quality_penalty(match)

    return score


def _section_for(match: dict[str, Any]) -> str:
    if _is_argentina_selection(match):
        return "selecciones"
    if _is_local_league(match) or _is_conmebol(match):
        return "ligas_locales"
    if _is_motorsport(match):
        return "motorsport"
    return "exterior"


def _sort_key(match: dict[str, Any]) -> tuple:
    return (
        _status_order(match),
        -_editorial_score(match),
        _parse_start_time(match.get("start_time")),
        _norm_text(match.get("competition")),
        _norm_text(match.get("home_team")),
    )


def _hero_sort_key(match: dict[str, Any]) -> tuple:
    return (
        -_editorial_score(match),
        _status_order(match),
        _parse_start_time(match.get("start_time")),
        _norm_text(match.get("competition")),
        _norm_text(match.get("home_team")),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Lectura de cache
# ─────────────────────────────────────────────────────────────────────────────

async def _read_sport_cache(sport: str) -> list[Match]:
    key = f"today:{sport}"
    data = await cache.get(key)
    if data is not None:
        return data
    data = await cache.get_last_valid(key)
    return data or []


async def _read_hoy_all() -> list[Match]:
    data = await cache.get("hoy:all")
    if data is not None:
        return data

    data = await cache.get_last_valid("hoy:all")
    if data:
        return data

    rebuilt: list[Match] = []
    for sport in settings.active_sports:
        rebuilt.extend(await _read_sport_cache(sport))
    return rebuilt


# ─────────────────────────────────────────────────────────────────────────────
# Armado de payload
# ─────────────────────────────────────────────────────────────────────────────

def _dedupe(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []

    for m in matches:
        key = str(
            m.get("id")
            or f"{m.get('sport')}|{m.get('competition')}|{m.get('home_team')}|{m.get('away_team')}|{m.get('start_time')}"
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(m)

    return out


def _build_sections(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sections = {
        "selecciones": {"key": "selecciones", "title": "Selecciones nacionales", "items": []},
        "ligas_locales": {"key": "ligas_locales", "title": "Ligas locales", "items": []},
        "exterior": {"key": "exterior", "title": "Argentinos en el exterior", "items": []},
        "motorsport": {"key": "motorsport", "title": "Motorsport argentino", "items": []},
    }

    for m in matches:
        cat = _section_for(m)
        m["category"] = cat
        sections[cat]["items"].append(m)

    for key in sections:
        sections[key]["items"].sort(key=_sort_key)

    return [
        sections[k]
        for k in ("selecciones", "ligas_locales", "exterior", "motorsport")
        if sections[k]["items"]
    ]


def _load_errors() -> dict[str, str]:
    try:
        from scraping.registry import LOAD_ERRORS  # type: ignore
        return LOAD_ERRORS
    except Exception:
        return {}


def _pick_hero(matches: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not matches:
        return None
    ranked = sorted(matches, key=_hero_sort_key)
    return ranked[0]


async def _build_summary(target_date: str) -> dict[str, Any]:
    raw_matches = await _read_hoy_all()
    matches = [_to_dict(m) for m in raw_matches]
    matches = _dedupe(matches)

    for m in matches:
        if not m.get("category"):
            m["category"] = _section_for(m)

    matches.sort(key=_sort_key)

    live = [m for m in matches if _norm_text(m.get("status")) == "live"]
    upcoming = [m for m in matches if _norm_text(m.get("status")) == "upcoming"]
    finished = [m for m in matches if _norm_text(m.get("status")) == "finished"]

    by_sport: dict[str, int] = defaultdict(int)
    for m in matches:
        by_sport[_norm_text(m.get("sport")) or "unknown"] += 1

    hero = _pick_hero(matches)

    return {
        "date": target_date,
        "updated_at": now_art().isoformat(),
        "hero": hero,
        "matches": matches,
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
        "by_sport": dict(by_sport),
        "sections": _build_sections(matches),
        "load_errors": _load_errors(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/hoy")
async def api_hoy(date: str | None = Query(default=None)):
    target_date = date or today_art()
    try:
        summary = await _build_summary(target_date)
        return JSONResponse(content={"ok": True, "date": target_date, "data": summary})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": str(e), "date": target_date},
        )


@router.get("/deporte/{sport}")
async def api_sport(sport: str, date: str | None = Query(default=None)):
    target_date = date or today_art()
    try:
        matches = [_to_dict(m) for m in await _read_sport_cache(sport)]
        matches = _dedupe(matches)

        for m in matches:
            if not m.get("category"):
                m["category"] = _section_for(m)

        matches.sort(key=_sort_key)

        return JSONResponse(
            content={
                "ok": True,
                "sport": sport,
                "date": target_date,
                "count": len(matches),
                "matches": matches,
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "sport": sport, "error": str(e)},
        )


@router.get("/resultados")
async def api_resultados(date: str | None = Query(default=None)):
    target_date = date or today_art()
    try:
        summary = await _build_summary(target_date)
        finished = [m for m in summary["matches"] if _norm_text(m.get("status")) == "finished"]
        finished.sort(key=_sort_key)

        return JSONResponse(
            content={
                "ok": True,
                "date": target_date,
                "count": len(finished),
                "matches": finished,
                "updated_at": summary["updated_at"],
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": str(e), "date": target_date},
        )


@router.get("/live")
async def api_live():
    target_date = today_art()
    try:
        summary = await _build_summary(target_date)
        live = [m for m in summary["matches"] if _norm_text(m.get("status")) == "live"]
        live.sort(key=_sort_key)

        return JSONResponse(
            content={
                "ok": True,
                "date": target_date,
                "count": len(live),
                "matches": live,
                "updated_at": summary["updated_at"],
            },
            headers={"Cache-Control": "no-store, max-age=0"},
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": str(e), "date": target_date},
        )


@router.get("/calendario")
async def api_calendario(date: str | None = Query(default=None)):
    target_date = date or today_art()
    try:
        summary = await _build_summary(target_date)
        return JSONResponse(
            content={
                "ok": True,
                "date": target_date,
                "hero": summary["hero"],
                "stats": summary["stats"],
                "sections": summary["sections"],
                "matches": summary["matches"],
                "updated_at": summary["updated_at"],
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": str(e), "date": target_date},
        )


@router.get("/health")
async def api_health():
    return {
        "ok": True,
        "today_art": today_art(),
        "now_art": now_art().isoformat(),
        "timezone": "America/Argentina/Buenos_Aires (UTC-3)",
        "load_errors": _load_errors(),
    }


@router.post("/cache/clear")
async def api_clear_cache(date: str | None = Query(default=None)):
    keys = ["hoy:all"] + [f"today:{s}" for s in settings.active_sports] + [f"live:{s}" for s in settings.active_sports]
    for k in keys:
        await cache.delete(k)

    return {
        "ok": True,
        "cleared": date or "all",
        "today_art": today_art(),
    }
