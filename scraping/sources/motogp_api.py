"""
Cliente para la API pública de MotoGP.
Endpoint base: api.motogp.com/riders-api/season/
No requiere autenticación para datos básicos de calendario y resultados.
"""
import httpx
from datetime import date

BASE = "https://api.motogp.com/riders-api/season"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Origin": "https://www.motogp.com",
    "Referer": "https://www.motogp.com/",
}


async def get_calendar(year: int | None = None) -> list:
    """Retorna el calendario de la temporada."""
    y = year or date.today().year
    url = f"{BASE}/{y}/events?test=false"
    async with httpx.AsyncClient(headers=HEADERS, timeout=15, follow_redirects=True) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.json()


async def get_event_sessions(event_id: str) -> list:
    """Retorna las sesiones de un evento (FP, Q, RACE)."""
    y = date.today().year
    url = f"{BASE}/{y}/events/{event_id}/categories"
    async with httpx.AsyncClient(headers=HEADERS, timeout=15, follow_redirects=True) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.json()


def is_active_event(event: dict) -> bool:
    """Verifica si un evento está en curso hoy."""
    today = date.today().isoformat()
    return (
        event.get("date_start", "") <= today <= event.get("date_end", "")
    )


def parse_event_to_match(event: dict, session_name: str = "Carrera") -> dict:
    """Convierte un evento MotoGP al formato crudo normalizable."""
    return {
        "competition": f"MotoGP — {event.get('name', 'Grand Prix')}",
        "home": session_name,
        "away": event.get("circuit", {}).get("name", ""),
        "home_score": None,
        "away_score": None,
        "status": "upcoming",
        "start_time": event.get("date_start", "")[:10],
        "source": "motogp",
        "raw": event,
    }
