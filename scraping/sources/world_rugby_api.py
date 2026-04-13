"""
World Rugby — API JSON oficial.
https://www.world.rugby usa endpoint REST para resultados y fixtures.
Sin key para datos básicos.
"""
import httpx
import logging
from datetime import date, timedelta

logger = logging.getLogger(__name__)

BASE = "https://api.wr-rims-prod.pulselive.com/rugby/v3"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://www.world.rugby/",
    "Origin": "https://www.world.rugby",
}

# IDs de competiciones en World Rugby API
COMPETITIONS = {
    "rugby_championship": 180,  # The Rugby Championship (ARG, NZ, AUS, SA)
    "world_cup_2027": 164,
    "super_rugby_americas": 406,  # SuperRugby Americas
    "nations_cup": 414,
}


async def get_matches_window(days_back: int = 1, days_fwd: int = 2) -> list[dict]:
    """Partidos en una ventana de días alrededor de hoy."""
    today = date.today()
    start = (today - timedelta(days=days_back)).strftime("%Y-%m-%d")
    end = (today + timedelta(days=days_fwd)).strftime("%Y-%m-%d")
    results = []

    for comp_id in COMPETITIONS.values():
        url = f"{BASE}/matches?startDate={start}&endDate={end}&competitionId={comp_id}&sort=asc&pageSize=20"
        try:
            async with httpx.AsyncClient(headers=HEADERS, timeout=12,
                                          follow_redirects=True) as c:
                r = await c.get(url)
                r.raise_for_status()
                data = r.json()
                matches = data.get("content", []) or []
                logger.info(f"[world_rugby] comp={comp_id} → {len(matches)}")
                results.extend(matches)
        except Exception as e:
            logger.debug(f"[world_rugby] comp={comp_id}: {e}")

    return results


def parse_match(m: dict) -> dict | None:
    """Convierte match World Rugby al formato normalizable."""
    try:
        teams = m.get("teams", []) or []
        if len(teams) < 2:
            return None

        home_team = teams[0]
        away_team = teams[1]
        home = (home_team.get("name") or "").strip()
        away = (away_team.get("name") or "").strip()
        if not home or not away:
            return None

        status_raw = (m.get("status") or "").lower()
        if status_raw in ("live", "inprogress"):
            status = "live"
        elif status_raw in ("complete", "fulltime", "final"):
            status = "finished"
        else:
            status = "upcoming"

        hs = home_team.get("score")
        as_ = away_team.get("score")
        try:
            hs = int(hs) if hs is not None else None
            as_ = int(as_) if as_ is not None else None
        except (ValueError, TypeError):
            hs = as_ = None

        comp_name = (m.get("competition") or {}).get("name", "World Rugby") or "World Rugby"

        start_time_arg = None
        ts = m.get("time", {}) or {}
        millis = ts.get("millis")
        if millis:
            try:
                from datetime import datetime, timezone
                dt = datetime.fromtimestamp(int(millis) / 1000, tz=timezone.utc)
                start_time_arg = f"{(dt.hour - 3) % 24:02d}:{dt.minute:02d}"
            except Exception:
                pass

        return {
            "home": home,
            "away": away,
            "competition": comp_name,
            "home_score": hs,
            "away_score": as_,
            "status": status,
            "minute": None,
            "start_time": start_time_arg,
            "source": "world_rugby",
            "raw": m,
        }
    except Exception:
        return None
