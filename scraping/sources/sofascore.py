"""
Cliente para la API no oficial de Sofascore.
Usada como fallback cuando no hay fuente oficial disponible.
"""
import httpx
from datetime import date


BASE = "https://api.sofascore.com/api/v1"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://www.sofascore.com/",
    "Origin": "https://www.sofascore.com",
}

# Sofascore sport slugs
SPORT_SLUGS: dict[str, str] = {
    "futbol":      "football",
    "tenis":       "tennis",
    "basquet":     "basketball",
    "rugby":       "rugby",
    "hockey":      "field-hockey",
    "voley":       "volleyball",
    "handball":    "handball",
    "futsal":      "futsal",
    "golf":        "golf",
    "esports":     "esports",
    "boxeo":       "boxing",
    "motorsport":  "motorsport",
    "motogp":      "motogp",
}


async def get_events_by_date(sport: str, target_date: date | None = None) -> dict:
    """Retorna eventos de un deporte para una fecha (default: hoy)."""
    d = target_date or date.today()
    slug = SPORT_SLUGS.get(sport, sport)
    url = f"{BASE}/sport/{slug}/scheduled-events/{d.isoformat()}"
    async with httpx.AsyncClient(headers=HEADERS, timeout=15, follow_redirects=True) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.json()


async def get_live_events(sport: str) -> dict:
    """Retorna eventos en vivo para un deporte."""
    slug = SPORT_SLUGS.get(sport, sport)
    url = f"{BASE}/sport/{slug}/events/live"
    async with httpx.AsyncClient(headers=HEADERS, timeout=15, follow_redirects=True) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.json()


async def get_event_detail(event_id: int | str) -> dict:
    url = f"{BASE}/event/{event_id}"
    async with httpx.AsyncClient(headers=HEADERS, timeout=15, follow_redirects=True) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.json()
