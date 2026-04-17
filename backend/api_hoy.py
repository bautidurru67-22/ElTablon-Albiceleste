"""
api_hoy.py — Endpoints agregados para El Tablón Albiceleste

Reglas:
- SIEMPRE usa ART (UTC-3)
- /hoy, /resultados, /live y /calendario leen cache central (hoy:all + today:*)
- Nunca bloquea request con scraping sincrónico
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
    # compat para frontend nuevo (/hoy client) y viejo
    if d.get("tv") is None and d.get("broadcast"):
        d["tv"] = d.get("broadcast")
    return d


def _norm_text(v: Any) -> str:
    return (str(v or "").strip().lower())


def _is_argentina_selection(match: dict[str, Any]) -> bool:
    hay = " ".join(
        [
            _norm_text(match.get("competition")),
            _norm_text(match.get("home_team")),
            _norm_text(match.get("away_team")),
            _norm_text(match.get("argentina_team")),
        ]
    )
    return (
        _norm_text(match.get("argentina_relevance")) == "seleccion"
        or "seleccion argentina" in hay
        or "selección argentina" in hay
        or ("argentina" in hay and ("sub 17" in hay or "sub-17" in hay or "sub 20" in hay or "sub-20" in hay or "sub 23" in hay or "sub-23" in hay))
    )


def _is_local_league(match: dict[str, Any]) -> bool:
    comp = _norm_text(match.get("competition"))
    if _norm_text(match.get("argentina_relevance")) == "club_arg":
        return True
    local_tokens = (
        "liga profesional",
        "primera nacional",
        "copa argentina",
        "reserva",
        "primera b",
        "b metro",
        "federal a",
        "primera c",
        "femenina",
    )
    return any(t in comp for t in local_tokens)


def _is_motorsport(match: dict[str, Any]) -> bool:
    return _norm_text(match.get("sport")) in {"motorsport", "motogp", "dakar"}


def _section_for(match: dict[str, Any]) -> str:
    if _is_argentina_selection(match):
        return "selecciones"
    if _is_motorsport(match):
        return "motorsport"
    if _is_local_league(match):
        return "ligas_locales"
    return "exterior"


def _sort_key(match: dict[str, Any]) -> tuple:
    status = _norm_text(match.get("status"))
    status_order = {"live": 0, "upcoming": 1, "finished": 2}
    section_order = {"selecciones": 0, "ligas_locales": 1, "exterior": 2, "motorsport": 3}
    section = match.get("category") or _section_for(match)
    rel = _norm_text(match.get("argentina_relevance"))
    rel_boost = {"seleccion": 0, "club_arg": 1, "jugador_arg": 2, "none": 3}.get(rel, 3)
    return (
        status_order.get(status, 9),
        section_order.get(section, 9),
        rel_boost,
        _norm_text(match.get("start_time")),
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
        key = str(m.get("id") or f"{m.get('sport')}|{m.get('competition')}|{m.get('home_team')}|{m.get('away_team')}|{m.get('start_time')}")
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
    return [sections[k] for k in ("selecciones", "ligas_locales", "exterior", "motorsport") if sections[k]["items"]]


def _load_errors() -> dict[str, str]:
    try:
        from scraping.registry import LOAD_ERRORS  # type: ignore
        return LOAD_ERRORS
    except Exception:
        return {}


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

    return {
        "date": target_date,
        "updated_at": now_art().isoformat(),
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
    """
    Retorna agenda argentina del día.
    date: YYYY-MM-DD en ART. Si no viene, usa hoy ART.
    """
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
