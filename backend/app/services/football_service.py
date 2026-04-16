import os
import httpx
from datetime import datetime

API_KEY = os.getenv("API_FOOTBALL_KEY")

BASE_URL = "https://v3.football.api-sports.io"

HEADERS = {
    "x-apisports-key": API_KEY
}

# 🔥 MAPEO REAL
LEAGUE_MAP = {
    "liga-profesional-argentina": 128,
    "primera-nacional": 129,
}

CURRENT_SEASON = datetime.now().year


async def fetch_standings(slug: str):
    league_id = LEAGUE_MAP.get(slug)

    if not league_id:
        return {"rows": []}

    url = f"{BASE_URL}/standings"

    params = {
        "league": league_id,
        "season": CURRENT_SEASON
    }

    async with httpx.AsyncClient() as client:
        res = await client.get(url, headers=HEADERS, params=params)
        data = res.json()

    try:
        standings = data["response"][0]["league"]["standings"][0]
    except:
        return {"rows": []}

    rows = []
    for team in standings:
        rows.append({
            "position": team["rank"],
            "team": team["team"]["name"],
            "points": team["points"],
            "played": team["all"]["played"],
            "won": team["all"]["win"],
            "draw": team["all"]["draw"],
            "lost": team["all"]["lose"],
        })

    return {
        "rows": rows
    }


async def fetch_fixtures(slug: str):
    league_id = LEAGUE_MAP.get(slug)

    if not league_id:
        return {"matches": []}

    url = f"{BASE_URL}/fixtures"

    params = {
        "league": league_id,
        "season": CURRENT_SEASON,
        "next": 20
    }

    async with httpx.AsyncClient() as client:
        res = await client.get(url, headers=HEADERS, params=params)
        data = res.json()

    matches = []

    for m in data.get("response", []):
        matches.append({
            "home": m["teams"]["home"]["name"],
            "away": m["teams"]["away"]["name"],
            "date": m["fixture"]["date"],
            "status": m["fixture"]["status"]["short"]
        })

    return {
        "matches": matches,
        "count": len(matches)
    }
