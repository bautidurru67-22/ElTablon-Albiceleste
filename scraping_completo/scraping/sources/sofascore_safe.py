"""
Sofascore — wrapper seguro.
En Railway puede devolver 403 (Cloudflare). Si eso ocurre, retorna {} sin romper nada.
Se usa como FALLBACK cuando la fuente primaria falla.
"""
import httpx
import logging
from datetime import date

logger = logging.getLogger(__name__)

BASE = "https://api.sofascore.com/api/v1"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "es-AR,es;q=0.9",
    "Referer": "https://www.sofascore.com/",
    "Origin": "https://www.sofascore.com",
}

SPORT_SLUGS = {
    "futbol": "football", "tenis": "tennis", "basquet": "basketball",
    "rugby": "rugby-union", "hockey": "field-hockey", "voley": "volleyball",
    "handball": "handball", "futsal": "futsal", "golf": "golf",
    "boxeo": "boxing", "motorsport": "motorsport", "motogp": "motogp",
}


async def get_events_by_date(sport: str, target_date: date | None = None) -> dict:
    d = target_date or date.today()
    slug = SPORT_SLUGS.get(sport, sport)
    url = f"{BASE}/sport/{slug}/scheduled-events/{d.isoformat()}"
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=12,
                                      follow_redirects=True) as c:
            r = await c.get(url)
            if r.status_code == 403:
                logger.warning(f"[sofascore] 403 Cloudflare para {sport} — fuente bloqueada en Railway")
                return {"events": []}
            r.raise_for_status()
            data = r.json()
            n = len(data.get("events", []))
            logger.info(f"[sofascore] {sport} {d} → {n} eventos")
            return data
    except httpx.HTTPStatusError as e:
        logger.warning(f"[sofascore] HTTP {e.response.status_code} {sport}")
        return {"events": []}
    except Exception as e:
        logger.warning(f"[sofascore] {sport}: {e}")
        return {"events": []}


async def get_live_events(sport: str) -> dict:
    slug = SPORT_SLUGS.get(sport, sport)
    url = f"{BASE}/sport/{slug}/events/live"
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=10,
                                      follow_redirects=True) as c:
            r = await c.get(url)
            if r.status_code == 403:
                return {"events": []}
            r.raise_for_status()
            data = r.json()
            n = len(data.get("events", []))
            logger.info(f"[sofascore/live] {sport} → {n}")
            return data
    except Exception as e:
        logger.warning(f"[sofascore/live] {sport}: {e}")
        return {"events": []}
