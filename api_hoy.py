"""
api_hoy.py — Endpoint /api/hoy para El Tablón Albiceleste

INTEGRACIÓN con tu framework:
  - FastAPI:  usar como router
  - Flask:    adaptable con pocas líneas
  - Next.js:  route handler análogo en /app/api/hoy/route.ts

CORRIGE:
  1. Timezone: SIEMPRE usa ART (UTC-3), nunca UTC
  2. Caché: se invalida automáticamente al cambiar de día
  3. Datos unificados: /hoy, /resultados, /calendario usan la misma fuente
"""

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from .scrapers.registry import get_today_summary, run_sport
from .scrapers.api_sports_base import today_art, now_art

router = APIRouter()


@router.get("/api/hoy")
async def api_hoy(date: str | None = Query(default=None)):
    """
    Retorna todos los partidos del día relevantes para Argentina.
    date: YYYY-MM-DD en timezone ART. Si no se provee, usa HOY en Argentina.

    CRÍTICO: La fecha se determina en ART, no en UTC.
    Ejemplo: si son las 21:30 UTC = 18:30 ART → devuelve partidos del mismo día ART.
             si son las 00:30 UTC = 21:30 ART anterior → aún devuelve partidos del día ART.
    """
    # Siempre usa ART para determinar "hoy"
    target_date = date or today_art()

    try:
        summary = await get_today_summary(target_date)
        return JSONResponse(content={
            "ok": True,
            "data": summary,
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": str(e), "date": target_date}
        )


@router.get("/api/deporte/{sport}")
async def api_sport(sport: str, date: str | None = Query(default=None)):
    """
    Retorna partidos de un deporte específico.
    NOTA: Lee del caché compartido con /api/hoy — no hace scraping nuevo.
    """
    target_date = date or today_art()
    try:
        matches = await run_sport(sport, target_date)
        return JSONResponse(content={
            "ok": True,
            "sport": sport,
            "date": target_date,
            "count": len(matches),
            "matches": matches,
        })
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "sport": sport, "error": str(e)}
        )


@router.get("/api/resultados")
async def api_resultados(date: str | None = Query(default=None)):
    """Retorna solo los partidos finalizados del día."""
    target_date = date or today_art()
    try:
        summary = await get_today_summary(target_date)
        finished = [m for m in summary["matches"] if m.get("status") == "finished"]
        return JSONResponse(content={
            "ok": True,
            "date": target_date,
            "count": len(finished),
            "matches": finished,
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})


@router.get("/api/live")
async def api_live():
    """Retorna solo los partidos en vivo AHORA. TTL: 20 segundos."""
    target_date = today_art()
    try:
        summary = await get_today_summary(target_date)
        live = [m for m in summary["matches"] if m.get("status") == "live"]
        return JSONResponse(
            content={"ok": True, "date": target_date, "count": len(live), "matches": live},
            headers={"Cache-Control": "no-store, max-age=0"},
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})


@router.get("/api/calendario")
async def api_calendario(date: str | None = Query(default=None)):
    """
    Retorna partidos para el calendario.
    Usa la misma fuente que /api/hoy — sin scraping adicional.
    """
    target_date = date or today_art()
    try:
        summary = await get_today_summary(target_date)
        return JSONResponse(content={
            "ok": True,
            "date": target_date,
            "stats": summary["stats"],
            "matches": summary["matches"],
            "updated_at": summary["updated_at"],
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})


@router.get("/api/health")
async def api_health():
    """Health check con info de timezone."""
    return {
        "ok": True,
        "today_art": today_art(),
        "now_art": now_art().isoformat(),
        "timezone": "America/Argentina/Buenos_Aires (UTC-3)",
    }
