"""
api_hoy.py — Endpoints agregados para El Tablón Albiceleste

Reglas:
- SIEMPRE usa ART (UTC-3)
- /hoy, /resultados, /live y /calendario leen cache central (hoy:all + today:*)
- Nunca bloquea request con scraping sincrónico
- Ranking editorial tipo producto:
    1) Selección Argentina
    2) Liga local argentina
    3) Copas CONMEBOL con clubes argentinos
    4) Argentinos en el exterior
    5) Motorsport argentino
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

    local_tokens = (
        "liga profesional",
        "liga profesional de futbol",
        "liga profesional de fútbol",
        "primera nacional",
        "primera b",
        "b metro",
        "federal a",
        "primera c",
        "primera d",
        "copa argentina",
        "reserva",
        "femenina",
        "torneo betano",
    )
    return any(t in comp for t in local_tokens)


def _is_conmebol(match: dict[str, Any]) -> bool:
    comp = _norm_text(match.get("competition"))
    return (
        "libertadores" in comp
        or "sudamericana" in comp
        or "recopa" in comp
        or "conmebol" in comp
    )


def _is_top_exterior(match: dict[str, Any]) -> bool:
    comp = _norm_text(match.get("competition"))
    top_tokens = (
        "premier league",
        "la liga",
        "serie a",
        "bundesliga",
        "ligue 1",
        "champions league",
        "europa league",
        "conference league",
    )
    return any(t in comp for t in top_tokens)


def _is_motorsport(match: dict[str, Any]) -> bool:
    return _norm_text(match.get("sport")) in {"motorsport", "motogp", "dakar"}


def _is_session_event(match: dict[str, Any]) -> bool:
    hay = _combined_text(match)
    session_tokens = (
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
    )
    return any(t in hay for t in session_tokens)


def _section_for(match: dict[str, Any]) -> str:
    if _is_argentina_selection(match):
        return "selecciones"
    if _is_motorsport(match):
        return "motorsport"
    if _is_local_league(match) or _is_conmebol(match):
        return "ligas_locales"
    return "exterior"


def _status_order(match: dict[str, Any]) -> int:
    status = _norm_text(match.get("status"))
    return {"live": 0, "upcoming": 1, "finished": 2}.get(status, 9)


def _parse_start_time(value: Any) -> str:
    text = str(value or "").strip()
    return text if text else "99:99"


def _editorial_score(match: dict[str, Any]) -> int:
    """
    Más alto = más importante.
    """
    score = 0
    hay = _combined_text(match)
    status = _norm_text(match.get("status"))
    relevance = _norm_text(match.get("argentina_relevance"))
    sport = _norm_text(match.get("sport"))

    # Base por relevancia argentina
    if relevance == "seleccion":
        score += 1000
    elif relevance == "club_arg":
        score += 700
    elif relevance == "jugador_arg":
        score += 450

    # Fútbol manda editorialmente
    if sport == "futbol":
        score += 220
    elif sport == "basquet":
        score += 120
    elif sport == "tenis":
        score += 100
    elif sport == "rugby":
        score += 90
    elif sport == "hockey":
        score += 90
    elif sport == "voley":
        score += 80
    elif _is_motorsport(match):
        score += 40

    # Selección nacional
    if _is_argentina_selection(match):
        score += 1200

    # Ligas locales y copas
    if _is_local_league(match):
        score += 900

    if _is_conmebol(match):
        score += 800

    # Exterior top
    if _is_top_exterior(match):
        score += 280

    # Status
    if status == "live":
        score += 350
    elif status == "upcoming":
        score += 140
    elif status == "finished":
        score += 40

    # Bonus por tener argentino identificado
    if _norm_text(match.get("argentina_team")):
        score += 50

    # Penalizaciones editoriales
    if _is_motorsport(match):
        score -= 120

    if _is_session_event(match):
        score -= 260

    # B / II / reserva bajan prioridad de hero
    if " ii" in f" {hay}" or " reserva" in f" {hay}" or " filial" in hay:
        score -= 180

    # Amistosos bajan
    if "amistoso" in hay or "friendly" in hay:
        score -= 130

    # Si competencia sigue genérica, penalizar
    if _norm_text(match.get("competition")) in {"futbol", "fútbol", "football", "soccer"}:
        score -= 120

    return score


def _sort_key(match: dict[str, Any]) -> tuple:
    """
    Orden visual general:
    - live antes
    - mayor score editorial antes
    - hora antes
    """
    return (
        _status_order(match),
        -_editorial_score(match),
        _parse_start_time(match.get("start_time")),
        _norm_text(match.get("competition")),
        _norm_text(match.get("home_team")),
    )


def _hero_sort_key(match: dict[str, Any]) -> tuple:
    """
    Orden del hero:
    - mayor score editorial
    - live antes
    - hora antes
    """
    return (
        -_editorial_score(match),
        _status_order(match),
        _parse_start_time(match.get("start_time")),
        _norm_text(match.get("competition")),
    )


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
