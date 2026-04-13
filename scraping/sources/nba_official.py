"""
NBA API oficial — cdn.nba.com. Gratuita, sin key, estable.
Retorna scoreboard del día con todos los partidos NBA.
"""
import httpx
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

SCOREBOARD_URL = "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json"
SCHEDULE_URL   = "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
}

# Jugadores argentinos activos NBA/G-League (normalizado, sin acentos)
ARG_NBA = {
    "campazzo", "bolmaro", "laprovittola", "vildoza",
    "deck", "brussino", "facu", "leandro", "nico",
}


async def get_today_scoreboard() -> dict:
    """Scoreboard del día. Retorna {} si falla."""
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=12,
                                      follow_redirects=True) as c:
            r = await c.get(SCOREBOARD_URL)
            r.raise_for_status()
            data = r.json()
            games = data.get("scoreboard", {}).get("games", [])
            logger.info(f"[nba] scoreboard → {len(games)} partidos")
            return data
    except Exception as e:
        logger.warning(f"[nba] scoreboard: {e}")
        return {}


def parse_games(data: dict) -> list[dict]:
    """Convierte games del scoreboard al formato normalizable."""
    games = data.get("scoreboard", {}).get("games", [])
    results = []
    for g in games:
        home_t = g.get("homeTeam", {})
        away_t = g.get("awayTeam", {})
        home_name = f"{home_t.get('teamCity', '')} {home_t.get('teamName', '')}".strip()
        away_name = f"{away_t.get('teamCity', '')} {away_t.get('teamName', '')}".strip()

        # Buscar jugadores ARG en los rosters
        home_has_arg = _has_arg_player(home_t)
        away_has_arg = _has_arg_player(away_t)
        if not home_has_arg and not away_has_arg:
            continue

        gs = g.get("gameStatus", 1)
        if gs == 1:
            status = "upcoming"
        elif gs == 2:
            status = "live"
        else:
            status = "finished"

        hs = as_ = None
        if gs in (2, 3):
            try:
                hs = int(home_t.get("score", 0))
                as_ = int(away_t.get("score", 0))
            except (ValueError, TypeError):
                pass

        period = g.get("period", 0)
        gc = g.get("gameClock", "") or ""
        minute = f"C{period} {gc}".strip() if status == "live" and period else None

        start_time_arg = None
        ts = g.get("gameTimeUTC", "")
        if ts:
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                start_time_arg = f"{(dt.hour - 3) % 24:02d}:{dt.minute:02d}"
            except Exception:
                pass

        arg_team = home_name if home_has_arg else away_name

        results.append({
            "home": home_name,
            "away": away_name,
            "competition": "NBA",
            "home_score": hs,
            "away_score": as_,
            "status": status,
            "minute": minute,
            "start_time": start_time_arg,
            "source": "nba",
            "arg_team": arg_team,
            "raw": g,
        })
    logger.info(f"[nba] {len(results)} partidos con ARG")
    return results


def _has_arg_player(team: dict) -> bool:
    for p in team.get("players", []):
        name = (p.get("name") or p.get("familyName") or "").lower()
        if any(a in name for a in ARG_NBA):
            return True
    return False
