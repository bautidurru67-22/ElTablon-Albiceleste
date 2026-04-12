"""
rugby.py — Scraper de rugby para El Tablón Albiceleste
Fuentes: Sofascore → ESPN → LiveScore
"""

import asyncio
import logging
from .api_sports_base import (
    NormalizedMatch, fetch_json,
    today_art, time_art, date_art,
    cache_get, cache_set, TTL,
)

logger = logging.getLogger("tablon.rugby")

_SOFA_HEADERS = {"Referer": "https://www.sofascore.com/"}

_ARG_RUGBY_KEYWORDS = {
    "argentina", "pumas", "jaguares", "casi", "sic", "newman",
    "hindú", "hindu", "san isidro", "belgrano", "regatas",
    "lomas", "cardenales", "alumni", "urba", "uar",
}

def _is_arg_rugby(home: str, away: str, comp: str) -> bool:
    text = f"{home} {away} {comp}".lower()
    return any(k in text for k in _ARG_RUGBY_KEYWORDS)

async def _sofa_rugby(date: str) -> list[NormalizedMatch]:
    url = f"https://api.sofascore.com/api/v1/sport/rugby/scheduled-events/{date}"
    data = await fetch_json(url, headers=_SOFA_HEADERS)
    if not data:
        return []

    results = []
    for ev in data.get("events", []):
        try:
            home = ev.get("homeTeam", {}).get("name", "")
            away = ev.get("awayTeam", {}).get("name", "")
            comp = ev.get("tournament", {}).get("name", "")
            country = ev.get("tournament", {}).get("category", {}).get("country", {}).get("name", "")

            if country != "Argentina" and not _is_arg_rugby(home, away, comp):
                continue

            ts = ev.get("startTimestamp", 0)
            from datetime import datetime, timezone as tz_
            dt = datetime.fromtimestamp(ts, tz=tz_.utc)
            start_iso = dt.isoformat()
            match_date = date_art(start_iso)
            if match_date != date:
                continue

            status_raw = ev.get("status", {}).get("type", "notstarted")
            _map = {"notstarted": "upcoming", "inprogress": "live", "finished": "finished"}
            status = _map.get(status_raw, "upcoming")

            relevance = "seleccion" if "argentina" in f"{home} {away}".lower() else "club_arg"

            results.append(NormalizedMatch(
                sport="rugby",
                competition=comp,
                home_team=home,
                away_team=away,
                home_score=ev.get("homeScore", {}).get("current"),
                away_score=ev.get("awayScore", {}).get("current"),
                status=status,
                start_time=time_art(start_iso),
                date=match_date,
                argentina_relevance=relevance,
                source="sofascore",
                match_id=str(ev.get("id", "")),
            ))
        except Exception as e:
            logger.debug(f"[sofa_rugby] {e}")
    return results

async def _espn_rugby(date: str) -> list[NormalizedMatch]:
    date_str = date.replace("-", "")
    results = []
    for league_id, league_name in [("world.sr", "Super Rugby"), ("world.rc", "Rugby Championship")]:
        url = (
            f"https://site.api.espn.com/apis/site/v2/sports/rugby/"
            f"{league_id}/scoreboard?dates={date_str}&limit=30"
        )
        data = await fetch_json(url)
        if not data:
            continue
        for ev in data.get("events", []):
            try:
                comp_obj = ev.get("competitions", [{}])[0]
                competitors = comp_obj.get("competitors", [])
                home_c = next((c for c in competitors if c.get("homeAway") == "home"), {})
                away_c = next((c for c in competitors if c.get("homeAway") == "away"), {})
                home = home_c.get("team", {}).get("displayName", "")
                away = away_c.get("team", {}).get("displayName", "")
                if not _is_arg_rugby(home, away, league_name):
                    continue

                start_iso = comp_obj.get("date", "")
                match_date = date_art(start_iso) if start_iso else date
                if match_date != date:
                    continue

                status_type = comp_obj.get("status", {}).get("type", {}).get("name", "")
                status = "live" if "IN" in status_type else ("finished" if "FINAL" in status_type else "upcoming")

                results.append(NormalizedMatch(
                    sport="rugby",
                    competition=league_name,
                    home_team=home,
                    away_team=away,
                    home_score=int(home_c.get("score", 0) or 0) if status != "upcoming" else None,
                    away_score=int(away_c.get("score", 0) or 0) if status != "upcoming" else None,
                    status=status,
                    start_time=time_art(start_iso) if start_iso else "--:--",
                    date=match_date,
                    argentina_relevance="club_arg",
                    source="espn",
                ))
            except Exception as e:
                logger.debug(f"[espn_rugby] {e}")
    return results

async def get_rugby_today(date: str | None = None) -> list[dict]:
    d = date or today_art()
    cached = cache_get(f"rugby:{d}")
    if cached is not None:
        return cached

    sofa, espn = await asyncio.gather(
        _sofa_rugby(d), _espn_rugby(d), return_exceptions=True
    )
    all_m: list[NormalizedMatch] = []
    for r in [sofa, espn]:
        if not isinstance(r, Exception):
            all_m.extend(r)

    seen: dict[str, NormalizedMatch] = {}
    for m in all_m:
        k = f"{m.date}:{m.home_team.lower()[:8]}:{m.away_team.lower()[:8]}"
        if k not in seen:
            seen[k] = m

    status_o = {"live": 0, "upcoming": 1, "finished": 2}
    sorted_m = sorted(seen.values(), key=lambda m: (status_o.get(m.status, 9), m.start_time))
    output = [m.to_dict() for m in sorted_m]
    cache_set(f"rugby:{d}", output, TTL["today"])
    logger.info(f"[rugby] {len(output)} matches for {d}")
    return output
