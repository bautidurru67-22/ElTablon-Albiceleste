"""
API-Football (api-football.com / rapidapi) — fuente oficial multi-deporte.

Uso en El Tablón:
- Liga Profesional
- Primera Nacional
- Copa Argentina
- Libertadores
- Sudamericana

Variables de entorno:
  API_FOOTBALL_KEY
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

logger = logging.getLogger(__name__)

BASE = "https://v3.football.api-sports.io"
ART_TZ = ZoneInfo("America/Argentina/Buenos_Aires")

LEAGUE_IDS = {
    "liga_profesional": 128,
    "primera_nacional": 131,
    "copa_argentina": 132,
    "copa_libertadores": 13,
    "copa_sudamericana": 14,
    "supercopa": 481,
}


def _headers() -> dict:
    key = (os.getenv("API_FOOTBALL_KEY", "") or "").strip()
    if not key:
        return {}
    return {
        "x-rapidapi-key": key,
        "x-rapidapi-host": "v3.football.api-sports.io",
    }


def _today_art() -> str:
    return datetime.now(ART_TZ).strftime("%Y-%m-%d")


def _season_for_today() -> int:
    return datetime.now(ART_TZ).year


async def get_fixtures_today(league_id: int | None = None) -> list[dict]:
    """
    Retorna fixtures del día ART.
    Si league_id es None, consulta solo las ligas confiables definidas arriba.
    """
    key = (os.getenv("API_FOOTBALL_KEY", "") or "").strip()
    if not key:
        logger.warning("[api_football] API_FOOTBALL_KEY no configurado — saltando")
        return []

    target_date = _today_art()
    season = _season_for_today()
    results: list[dict] = []

    leagues = [league_id] if league_id else list(LEAGUE_IDS.values())

    async with httpx.AsyncClient(
        headers=_headers(),
        timeout=httpx.Timeout(12.0, connect=6.0),
        follow_redirects=True,
    ) as client:
        for lid in leagues:
            url = f"{BASE}/fixtures?league={lid}&season={season}&date={target_date}"
            try:
                r = await client.get(url)
                r.raise_for_status()
                data = r.json()
                fixtures = data.get("response", [])
                logger.info(f"[api_football] liga={lid} date={target_date} -> {len(fixtures)} fixtures")
                results.extend(fixtures)
            except httpx.HTTPStatusError as e:
                logger.warning(f"[api_football] HTTP {e.response.status_code} liga={lid}")
            except Exception as e:
                logger.warning(f"[api_football] error liga={lid}: {e}")

    return results


def parse_fixture(fix: dict) -> dict:
    """
    Convierte un fixture de API-Football al formato crudo esperado por el adapter.
    """
    f = fix.get("fixture", {}) or {}
    teams = fix.get("teams", {}) or {}
    goals = fix.get("goals", {}) or {}
    league = fix.get("league", {}) or {}

    raw_short = ((f.get("status") or {}).get("short") or "NS").upper()

    status_map = {
        "NS": "upcoming",
        "TBD": "upcoming",
        "PST": "upcoming",
        "1H": "live",
        "HT": "live",
        "2H": "live",
        "ET": "live",
        "BT": "live",
        "INT": "live",
        "P": "live",
        "FT": "finished",
        "AET": "finished",
        "PEN": "finished",
        "SUSP": "finished",
        "CANC": "finished",
        "ABD": "finished",
    }

    elapsed = (f.get("status") or {}).get("elapsed")
    minute = f"{elapsed}'" if elapsed not in (None, "") else None

    date_utc = f.get("date")
    start_time_art = None

    if date_utc:
        try:
            dt = datetime.fromisoformat(date_utc.replace("Z", "+00:00")).astimezone(ART_TZ)
            start_time_art = dt.strftime("%H:%M")
        except Exception:
            start_time_art = None

    return {
        "home": (teams.get("home") or {}).get("name", ""),
        "away": (teams.get("away") or {}).get("name", ""),
        "home_score": goals.get("home"),
        "away_score": goals.get("away"),
        "competition": league.get("name", ""),
        "status": status_map.get(raw_short, "upcoming"),
        "minute": minute,
        "start_time": start_time_art,
        "broadcast": None,
        "source": "api_football",
    }
