from __future__ import annotations

import os
import logging
import httpx
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

BASE = "https://v3.football.api-sports.io"
LEAGUES = {
    "liga-profesional": 128,
    "primera-nacional": 131,
    "copa-argentina": 132,
    "libertadores": 13,
    "sudamericana": 14,
}


def _raw_key() -> str:
    return (os.getenv("API_FOOTBALL_KEY", "") or "").strip()


def _is_placeholder_key(key: str) -> bool:
    if not key:
        return True
    bad = {
        "TU_API_KEY_REAL",
        "API_KEY",
        "YOUR_API_KEY",
        "CHANGE_ME",
        "test",
        "xxxxx",
        "REPLACE_ME",
    }
    return key in bad


def _headers(key: str) -> dict:
    return {
        "x-rapidapi-key": key,
        "x-rapidapi-host": "v3.football.api-sports.io",
    }


def _season_now() -> int:
    return datetime.utcnow().year


def _normalize_status(short: str | None) -> str:
    m = {
        "NS": "upcoming",
        "TBD": "upcoming",
        "PST": "upcoming",
        "1H": "live",
        "HT": "live",
        "2H": "live",
        "ET": "live",
        "BT": "live",
        "P": "live",
        "FT": "finished",
        "AET": "finished",
        "PEN": "finished",
        "CANC": "finished",
        "ABD": "finished",
    }
    return m.get((short or "").upper(), "upcoming")


async def _fetch_standings(
    client: httpx.AsyncClient,
    league_id: int,
    seasons_to_try: list[int],
) -> tuple[list[dict], str]:
    label = ""
    for season in seasons_to_try:
        try:
            res = await client.get(f"{BASE}/standings?league={league_id}&season={season}")
            res.raise_for_status()
            data: dict[str, Any] = res.json()
            league = (((data.get("response") or [{}])[0].get("league") or {}))
            raw = ((league.get("standings") or [[]])[0])

            standings = [
                {
                    "position": row.get("rank"),
                    "team": (row.get("team") or {}).get("name"),
                    "points": row.get("points"),
                    "played": ((row.get("all") or {}).get("played")),
                    "goal_diff": row.get("goalsDiff"),
                    "form": row.get("form"),
                }
                for row in raw
                if (row.get("team") or {}).get("name")
            ]
            label = league.get("name") or label
            if standings:
                return standings, label
        except Exception as e:
            logger.warning(f"[football_overview] standings season={season} error: {e}")
    return [], label


async def _fetch_fixtures(
    client: httpx.AsyncClient,
    league_id: int,
    seasons_to_try: list[int],
) -> list[dict]:
    for season in seasons_to_try:
        try:
            # intentamos próximos partidos
            res = await client.get(f"{BASE}/fixtures?league={league_id}&season={season}&next=20")
            res.raise_for_status()
            data: dict[str, Any] = res.json()
            rows = data.get("response") or []

            fixtures = [
                {
                    "date": ((item.get("fixture") or {}).get("date")),
                    "status": _normalize_status((((item.get("fixture") or {}).get("status") or {}).get("short"))),
                    "home": (((item.get("teams") or {}).get("home") or {}).get("name")),
                    "away": (((item.get("teams") or {}).get("away") or {}).get("name")),
                    "home_score": ((item.get("goals") or {}).get("home")),
                    "away_score": ((item.get("goals") or {}).get("away")),
                    "round": ((item.get("league") or {}).get("round")),
                }
                for item in rows
                if (((item.get("teams") or {}).get("home") or {}).get("name")
                    and ((item.get("teams") or {}).get("away") or {}).get("name"))
            ]
            if fixtures:
                return fixtures

            # fallback: últimos partidos
            res2 = await client.get(f"{BASE}/fixtures?league={league_id}&season={season}&last=20")
            res2.raise_for_status()
            data2: dict[str, Any] = res2.json()
            rows2 = data2.get("response") or []
            fixtures2 = [
                {
                    "date": ((item.get("fixture") or {}).get("date")),
                    "status": _normalize_status((((item.get("fixture") or {}).get("status") or {}).get("short"))),
                    "home": (((item.get("teams") or {}).get("home") or {}).get("name")),
                    "away": (((item.get("teams") or {}).get("away") or {}).get("name")),
                    "home_score": ((item.get("goals") or {}).get("home")),
                    "away_score": ((item.get("goals") or {}).get("away")),
                    "round": ((item.get("league") or {}).get("round")),
                }
                for item in rows2
                if (((item.get("teams") or {}).get("home") or {}).get("name")
                    and ((item.get("teams") or {}).get("away") or {}).get("name"))
            ]
            if fixtures2:
                return fixtures2
        except Exception as e:
            logger.warning(f"[football_overview] fixtures season={season} error: {e}")
    return []


async def get_football_overview(competition: str = "liga-profesional") -> dict:
    league_id = LEAGUES.get(competition, LEAGUES["liga-profesional"])
    key = _raw_key()

    if _is_placeholder_key(key):
        return {
            "competition": competition,
            "competition_label": competition.replace("-", " ").title(),
            "standings": [],
            "fixtures": [],
            "source": "api_football",
            "error": "API_FOOTBALL_KEY no configurado",
        }

    seasons_to_try = [_season_now(), _season_now() - 1]
    standings: list[dict] = []
    fixtures: list[dict] = []
    competition_label = competition.replace("-", " ").title()
    error = None

    async with httpx.AsyncClient(
        headers=_headers(key),
        timeout=httpx.Timeout(15.0, connect=7.0),
        follow_redirects=True,
    ) as client:
        standings, fetched_label = await _fetch_standings(client, league_id, seasons_to_try)
        if fetched_label:
            competition_label = fetched_label

        fixtures = await _fetch_fixtures(client, league_id, seasons_to_try)

    if not standings and not fixtures:
        error = "Sin datos de standings/fixtures para la competencia seleccionada"

    return {
        "competition": competition,
        "competition_label": competition_label,
        "standings": standings,
        "fixtures": fixtures,
        "source": "api_football",
        **({"error": error} if error else {}),
    }
