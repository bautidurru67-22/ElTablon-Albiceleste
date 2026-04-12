"""
Sofascore API — fuente principal del sistema.
API no oficial, reverse-engineered desde la web app.
Headers que imitan Chrome para evitar bloqueos de Cloudflare.
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
    "Accept-Language": "es-AR,es;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.sofascore.com/",
    "Origin": "https://www.sofascore.com",
    "Cache-Control": "no-cache",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-site",
}

# Slugs de Sofascore por deporte interno
SPORT_SLUGS: dict[str, str] = {
    "futbol":     "football",
    "tenis":      "tennis",
    "basquet":    "basketball",
    "rugby":      "rugby-union",      # NO american-football
    "hockey":     "field-hockey",
    "voley":      "volleyball",
    "handball":   "handball",
    "futsal":     "futsal",
    "golf":       "golf",
    "esports":    "esports",
    "boxeo":      "boxing",
    "motorsport": "motorsport",
    "motogp":     "motogp",
    "polo":       "polo",
}


async def get_events_by_date(sport: str, target_date: date | None = None) -> dict:
    d = target_date or date.today()
    slug = SPORT_SLUGS.get(sport, sport)
    url = f"{BASE}/sport/{slug}/scheduled-events/{d.isoformat()}"
    try:
        async with httpx.AsyncClient(
            headers=HEADERS,
            timeout=httpx.Timeout(15.0, connect=8.0),
            follow_redirects=True,
        ) as client:
            r = await client.get(url)
            r.raise_for_status()
            data = r.json()
            n = len(data.get("events", []))
            logger.info(f"[sofascore] {sport} scheduled {d} → {n} eventos")
            return data
    except httpx.HTTPStatusError as e:
        logger.warning(f"[sofascore] HTTP {e.response.status_code} {sport} scheduled")
        return {"events": []}
    except Exception as e:
        logger.warning(f"[sofascore] error {sport} scheduled: {e}")
        return {"events": []}


async def get_live_events(sport: str) -> dict:
    slug = SPORT_SLUGS.get(sport, sport)
    url = f"{BASE}/sport/{slug}/events/live"
    try:
        async with httpx.AsyncClient(
            headers=HEADERS,
            timeout=httpx.Timeout(12.0, connect=6.0),
            follow_redirects=True,
        ) as client:
            r = await client.get(url)
            r.raise_for_status()
            data = r.json()
            n = len(data.get("events", []))
            logger.info(f"[sofascore] {sport} live → {n} eventos")
            return data
    except httpx.HTTPStatusError as e:
        logger.warning(f"[sofascore] HTTP {e.response.status_code} {sport} live")
        return {"events": []}
    except Exception as e:
        logger.warning(f"[sofascore] error {sport} live: {e}")
        return {"events": []}
