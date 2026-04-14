from __future__ import annotations

import os
import logging
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)

BASE = "https://v3.football.api-sports.io"
LEAGUES = {
    "liga-profesional": 128,
    "primera-nacional": 131,
    "copa-argentina": 132,
    "libertadores": 13,
    "sudamericana": 14,
}


def _headers() -> dict:
    key = os.getenv("API_FOOTBALL_KEY", "")
    if not key:
        return {}
    return {
        "x-rapidapi-key": key,
        "x-rapidapi-host": "v3.football.api-sports.io",
    }


def _season_now() -> int:
    return datetime.utcnow().year


async def get_football_overview(competition: str = "liga-profesional") -> dict:
    league_id = LEAGUES.get(competition, LEAGUES["liga-profesional"])
    season = _season_now()

    if not os.getenv("API_FOOTBALL_KEY"):
        return {
            "competition": competition,
            "competition_label": competition.replace("-", " ").title(),
            "standings": [],
            "fixtures": [],
            "source": "api_football",
            "error": "API_FOOTBALL_KEY no configurado",
        }

    standings: list[dict] = []
    fixtures: list[dict] = []

    async with httpx.AsyncClient(headers=_headers(), timeout=httpx.Timeout(12.0, connect=6.0), follow_redirects=True) as client:
        try:
            s_res = await client.get(f"{BASE}/standings?league={league_id}&season={season}")
            s_res.raise_for_status()
            s_json = s_res.json()
            league = (((s_json.get("response") or [{}])[0].get("league") or {}))
            raw_standings = ((league.get("standings") or [[]])[0])
            standings = [
                {
                    "position": row.get("rank"),
                    "team": (row.get("team") or {}).get("name"),
                    "points": row.get("points"),
                    "played": ((row.get("all") or {}).get("played")),
                    "goal_diff": ((row.get("goalsDiff"))),
                    "form": row.get("form"),
                }
                for row in raw_standings
            ]
            competition_label = league.get("name") or competition.replace("-", " ").title()
        except Exception as e:
            logger.warning(f"[football_overview] standings error: {e}")
            competition_label = competition.replace("-", " ").title()

        try:
            f_res = await client.get(f"{BASE}/fixtures?league={league_id}&season={season}&next=20")
            f_res.raise_for_status()
            f_json = f_res.json()
            fixtures = [
                {
                    "date": ((item.get("fixture") or {}).get("date")),
                    "status": (((item.get("fixture") or {}).get("status") or {}).get("short")),
                    "home": (((item.get("teams") or {}).get("home") or {}).get("name")),
                    "away": (((item.get("teams") or {}).get("away") or {}).get("name")),
                    "home_score": ((item.get("goals") or {}).get("home")),
                    "away_score": ((item.get("goals") or {}).get("away")),
                    "round": ((item.get("league") or {}).get("round")),
                }
                for item in (f_json.get("response") or [])
            ]
        except Exception as e:
            logger.warning(f"[football_overview] fixtures error: {e}")

    return {
        "competition": competition,
        "competition_label": competition_label,
        "standings": standings,
        "fixtures": fixtures,
        "source": "api_football",
    }
