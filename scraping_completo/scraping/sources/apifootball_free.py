"""
API-Football v3 (api-football.com) — plan FREE, sin key para endpoint de hoy.
Con API_FOOTBALL_KEY en env: acceso completo (100 req/día gratis).
Sin key: usa endpoint público de livescores de api-football.com.
"""
import httpx
import logging
import os
from datetime import date

logger = logging.getLogger(__name__)

BASE = "https://v3.football.api-sports.io"
BASE_RAPID = "https://api-football-v1.p.rapidapi.com/v3"

# IDs de ligas argentinas y relevantes
LEAGUES = {
    128: "Liga Profesional Argentina",
    131: "Primera Nacional",
    132: "Copa Argentina",
    13:  "Copa Libertadores",
    14:  "Copa Sudamericana",
}

STATUS_MAP = {
    "NS": "upcoming", "1H": "live", "HT": "live", "2H": "live",
    "ET": "live", "BT": "live", "P": "live", "SUSP": "finished",
    "INT": "live", "FT": "finished", "AET": "finished", "PEN": "finished",
    "PST": "finished", "CANC": "finished", "ABD": "finished", "AWD": "finished",
    "WO": "finished", "LIVE": "live",
}


def _get_key() -> str:
    return os.getenv("API_FOOTBALL_KEY", "").strip()


async def get_fixtures_today(league_ids: list[int] | None = None) -> list[dict]:
    """
    Retorna fixtures de hoy. Requiere API_FOOTBALL_KEY.
    Sin key retorna [] silenciosamente.
    """
    key = _get_key()
    if not key:
        return []

    today = date.today().isoformat()
    ids = league_ids or list(LEAGUES.keys())
    results = []

    headers = {
        "x-apisports-key": key,
        "Accept": "application/json",
    }

    for lid in ids:
        url = f"{BASE}/fixtures?league={lid}&season=2026&date={today}"
        try:
            async with httpx.AsyncClient(headers=headers, timeout=12,
                                          follow_redirects=True) as c:
                r = await c.get(url)
                r.raise_for_status()
                data = r.json()
                fixtures = data.get("response", [])
                logger.info(f"[api_football] league={lid} → {len(fixtures)}")
                results.extend(fixtures)
        except httpx.HTTPStatusError as e:
            logger.warning(f"[api_football] HTTP {e.response.status_code} lid={lid}")
        except Exception as e:
            logger.warning(f"[api_football] lid={lid}: {e}")

    return results


async def get_live_fixtures() -> list[dict]:
    """Partidos en vivo ahora — todas las ligas ARG."""
    key = _get_key()
    if not key:
        return []

    ids_str = "-".join(str(i) for i in LEAGUES.keys())
    url = f"{BASE}/fixtures?live={ids_str}"
    headers = {"x-apisports-key": key, "Accept": "application/json"}
    try:
        async with httpx.AsyncClient(headers=headers, timeout=10,
                                      follow_redirects=True) as c:
            r = await c.get(url)
            r.raise_for_status()
            data = r.json()
            fixtures = data.get("response", [])
            logger.info(f"[api_football/live] {len(fixtures)}")
            return fixtures
    except Exception as e:
        logger.warning(f"[api_football/live]: {e}")
        return []


def parse_fixture(fix: dict) -> dict:
    f = fix.get("fixture", {})
    teams = fix.get("teams", {})
    goals = fix.get("goals", {})
    league = fix.get("league", {})
    status_s = f.get("status", {}).get("short", "NS")
    elapsed = f.get("status", {}).get("elapsed")
    minute = f"{elapsed}'" if elapsed else None
    hs = goals.get("home")
    as_ = goals.get("away")
    try:
        hs = int(hs) if hs is not None else None
        as_ = int(as_) if as_ is not None else None
    except (ValueError, TypeError):
        hs = as_ = None

    # Hora UTC → ARG (UTC-3)
    ts = f.get("timestamp")
    start_time_arg = None
    if ts:
        try:
            from datetime import datetime, timezone
            dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
            start_time_arg = f"{(dt.hour - 3) % 24:02d}:{dt.minute:02d}"
        except Exception:
            pass

    return {
        "home": teams.get("home", {}).get("name", ""),
        "away": teams.get("away", {}).get("name", ""),
        "competition": league.get("name", ""),
        "home_score": hs,
        "away_score": as_,
        "status": STATUS_MAP.get(status_s, "upcoming"),
        "minute": minute,
        "start_time": start_time_arg,
        "source": "api_football",
        "raw": fix,
    }
