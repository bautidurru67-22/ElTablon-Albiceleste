"""
Clientes para APIs públicas de F1.
- OpenF1 API: openf1.org — sesiones en vivo, telemetría, posiciones
- Ergast API: ergast.com/mrd — historial, calendario, resultados (legacy, sigue activo)
Ambas son gratuitas y no requieren autenticación.
"""
import httpx
from datetime import date

OPENF1_BASE = "https://api.openf1.org/v1"
ERGAST_BASE  = "https://ergast.com/api/f1"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}


async def get_current_session() -> dict:
    """Sesión F1 activa ahora mismo (qualifying, race, practice)."""
    url = f"{OPENF1_BASE}/sessions?date_start>={date.today().isoformat()}&limit=5"
    async with httpx.AsyncClient(headers=HEADERS, timeout=15) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.json()


async def get_current_race_weekend() -> dict:
    """Próxima carrera del calendario F1 (Ergast)."""
    year = date.today().year
    url = f"{ERGAST_BASE}/{year}.json"
    async with httpx.AsyncClient(headers=HEADERS, timeout=15) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.json()


async def get_last_race_result() -> dict:
    """Último resultado de carrera F1."""
    url = f"{ERGAST_BASE}/current/last/results.json"
    async with httpx.AsyncClient(headers=HEADERS, timeout=15) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.json()


def parse_race_to_match(race: dict, session_type: str = "Carrera") -> dict:
    """
    Convierte un race dict de Ergast al formato crudo normalizable.
    Retorna dict listo para MotorsportNormalizer.
    """
    return {
        "competition": f"F1 {race.get('raceName', 'Grand Prix')}",
        "home": session_type,
        "away": race.get("Circuit", {}).get("circuitName", ""),
        "home_score": None,
        "away_score": None,
        "status": "upcoming",
        "start_time": race.get("time", ""),
        "source": "ergast",
        "raw": race,
    }
