"""
API-Football (api-football.com / rapidapi) — fuente oficial multi-deporte.
Plan FREE: 100 requests/día. Cubre Liga Profesional, Libertadores, Sudamericana.

Variables de entorno requeridas:
  API_FOOTBALL_KEY — clave de RapidAPI o api-football.com directa
"""
import httpx
import logging
import os
from datetime import date

logger = logging.getLogger(__name__)

BASE = "https://v3.football.api-sports.io"

# IDs de ligas argentinas en API-Football
LEAGUE_IDS = {
    "liga_profesional": 128,
    "primera_nacional": 131,
    "copa_argentina": 132,
    "copa_libertadores": 13,
    "copa_sudamericana": 14,
    "supercopa": 481,
}


def _headers() -> dict:
    key = os.getenv("API_FOOTBALL_KEY", "")
    if not key:
        return {}
    return {
        "x-rapidapi-key": key,
        "x-rapidapi-host": "v3.football.api-sports.io",
    }


async def get_fixtures_today(league_id: int | None = None) -> list[dict]:
    """Retorna fixtures del día. Si league_id es None, retorna de todas las ligas ARG."""
    key = os.getenv("API_FOOTBALL_KEY", "")
    if not key:
        logger.warning("[api_football] API_FOOTBALL_KEY no configurado — saltando")
        return []

    today = date.today().isoformat()
    results = []

    leagues = [league_id] if league_id else list(LEAGUE_IDS.values())
    for lid in leagues:
        url = f"{BASE}/fixtures?league={lid}&season=2026&date={today}"
        try:
            async with httpx.AsyncClient(
                headers=_headers(),
                timeout=httpx.Timeout(12.0, connect=6.0),
                follow_redirects=True,
            ) as client:
                r = await client.get(url)
                r.raise_for_status()
                data = r.json()
                fixtures = data.get("response", [])
                logger.info(f"[api_football] liga={lid} → {len(fixtures)} fixtures")
                results.extend(fixtures)
        except httpx.HTTPStatusError as e:
            logger.warning(f"[api_football] HTTP {e.response.status_code} liga={lid}")
        except Exception as e:
            logger.warning(f"[api_football] error liga={lid}: {e}")

    return results


def parse_fixture(fix: dict) -> dict:
    """Convierte un fixture de API-Football al formato crudo esperado por el normalizer."""
    f = fix.get("fixture", {})
    teams = fix.get("teams", {})
    goals = fix.get("goals", {})
    league = fix.get("league", {})

    status = f.get("status", {}).get("short", "NS")
    STATUS_MAP = {
        "NS": "upcoming", "1H": "live", "HT": "live", "2H": "live",
        "ET": "live", "P": "live", "FT": "finished", "AET": "finished",
        "PEN": "finished", "SUSP": "finished", "INT": "live",
        "PST": "finished", "CANC": "finished", "ABD": "finished",
    }

    elapsed = f.get("status", {}).get("elapsed")
    minute = f"{elapsed}'" if elapsed else None

    return {
        "home": teams.get("home", {}).get("name", ""),
        "away": teams.get("away", {}).get("name", ""),
        "home_score": goals.get("home"),
        "away_score": goals.get("away"),
        "competition": league.get("name", ""),
        "status": STATUS_MAP.get(status, "upcoming"),
        "minute": minute,
        "start_time": None,
        "source": "api_football",
    }
