"""
api_hoy.py — Endpoints agregados para El Tablón Albiceleste

Reglas:
- SIEMPRE usa ART (UTC-3)
- /hoy, /resultados, /live y /calendario leen la misma fuente agregada
- cache invalidado naturalmente por fecha
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from api_sports_base import now_art, today_art
from scraping.registry import LOAD_ERRORS, clear_cache, get_today_summary, run_sport

router = APIRouter(tags=["hoy"])


@router.get("/hoy")
async def api_hoy(date: str | None = Query(default=None)):
    """
    Retorna agenda argentina del día.
    date: YYYY-MM-DD en ART. Si no viene, usa hoy ART.
    """
    target_date = date or today_art()

    try:
        summary = await get_today_summary(target_date)
        return JSONResponse(
            content={
                "ok": True,
                "date": target_date,
                "data": summary,
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": str(e), "date": target_date},
        )


@router.get("/deporte/{sport}")
async def api_sport(sport: str, date: str | None = Query(default=None)):
    """
    Devuelve solo un deporte, usando la misma lógica Argentina-first.
    """
    target_date = date or today_art()

    try:
        matches = await run_sport(sport, target_date)
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
    """
    Retorna solo finalizados del día.
    """
    target_date = date or today_art()

    try:
        summary = await get_today_summary(target_date)
        finished = [m for m in summary["matches"] if m.get("status") == "finished"]
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
    """
    Retorna solo lo EN VIVO ahora.
    """
    target_date = today_art()

    try:
        summary = await get_today_summary(target_date)
        live = [m for m in summary["matches"] if m.get("status") == "live"]
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
    """
    Retorna agenda de calendario del día, usando la misma fuente de /hoy.
    """
    target_date = date or today_art()

    try:
        summary = await get_today_summary(target_date)
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
        "load_errors": LOAD_ERRORS,
    }


@router.post("/cache/clear")
async def api_clear_cache(date: str | None = Query(default=None)):
    """
    Limpieza manual de cache.
    - sin date: limpia todo
    - con date=YYYY-MM-DD: limpia solo ese día
    """
    clear_cache(date=date)
    return {
        "ok": True,
        "cleared": date or "all",
        "today_art": today_art(),
    }
