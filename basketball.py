"""
basketball.py — Scraper de básquet para El Tablón Albiceleste
Fuentes: ESPN (LNB + NBA) → Sofascore
"""

import asyncio
import logging
from .api_sports_base import (
    NormalizedMatch, fetch_json,
    today_art, time_art, date_art,
    cache_get, cache_set, TTL, detect_argentina_relevance,
)

logger = logging.getLogger("tablon.basketball")

_SOFA_HEADERS = {"Referer": "https://www.sofascore.com/"}

_ARG_BBALL_KEYWORDS = {
    "ferro", "instituto", "boca", "quimsa", "peñarol",
    "obras", "san lorenzo", "regatas", "comunicaciones",
    "argentina", "pico", "atenas", "platense",
}

def _is_arg_bball(home: str, away: str, comp: str) -> bool:
    text = f"{home} {away} {comp}".lower()
    return any(k in text for k in _ARG_BBALL_KEYWORDS)

async def _espn_basketball(date: str) -> list[NormalizedMatch]:
    results = []
    date_str = date.replace("-", "")
    leagues = [
        ("nba",   "NBA"),
        ("arg.1", "Liga Nacional de Básquet"),
    ]
    for league_id, league_name in leagues:
        url = (
            f"https://site.api.espn.com/apis/site/v2/sports/basketball/"
            f"{league_id}/scoreboard?dates={date_str}&limit=50"
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
                if not home or not away:
                    continue

                if league_id == "nba" and not _is_arg_bball(home, away, ""):
                    # For NBA only include if there's context (we'll enrich later)
                    pass  # Include all NBA — visible sport

                start_iso = comp_obj.get("date", "")
                match_date = date_art(start_iso) if start_iso else date
                if match_date != date:
                    continue

                status_type = comp_obj.get("status", {}).get("type", {}).get("name", "")
                status = "live" if "IN" in status_type else ("finished" if "FINAL" in status_type else "upcoming")

                home_score_raw = home_c.get("score")
                away_score_raw = away_c.get("score")

                period = comp_obj.get("status", {}).get("type", {}).get("shortDetail", "")

                is_arg = league_id == "arg.1" or _is_arg_bball(home, away, league_name)
                relevance = "club_arg" if is_arg and league_id == "arg.1" else ("jugador_arg" if is_arg else "none")

                results.append(NormalizedMatch(
                    sport="basquet",
                    competition=league_name,
                    home_team=home,
                    away_team=away,
                    home_score=int(home_score_raw) if home_score_raw else None,
                    away_score=int(away_score_raw) if away_score_raw else None,
                    status=status,
                    start_time=time_art(start_iso) if start_iso else "--:--",
                    date=match_date,
                    period=period,
                    argentina_relevance=relevance,
                    source="espn",
                    home_logo=home_c.get("team", {}).get("logo"),
                    away_logo=away_c.get("team", {}).get("logo"),
                    match_id=str(ev.get("id", "")),
                ))
            except Exception as e:
                logger.debug(f"[espn_bball] {e}")
    return results

async def _sofa_basketball(date: str) -> list[NormalizedMatch]:
    url = f"https://api.sofascore.com/api/v1/sport/basketball/scheduled-events/{date}"
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
            if country != "Argentina" and not _is_arg_bball(home, away, comp):
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

            results.append(NormalizedMatch(
                sport="basquet",
                competition=comp,
                home_team=home,
                away_team=away,
                home_score=ev.get("homeScore", {}).get("current"),
                away_score=ev.get("awayScore", {}).get("current"),
                status=status,
                start_time=time_art(start_iso),
                date=match_date,
                argentina_relevance="club_arg" if country == "Argentina" else "jugador_arg",
                source="sofascore",
                match_id=str(ev.get("id", "")),
            ))
        except Exception as e:
            logger.debug(f"[sofa_bball] {e}")
    return results

async def get_basketball_today(date: str | None = None) -> list[dict]:
    d = date or today_art()
    cached = cache_get(f"basketball:{d}")
    if cached is not None:
        return cached

    espn, sofa = await asyncio.gather(
        _espn_basketball(d), _sofa_basketball(d), return_exceptions=True
    )
    all_m: list[NormalizedMatch] = []
    for r in [espn, sofa]:
        if not isinstance(r, Exception):
            all_m.extend(r)

    # Dedup by home+away+date
    seen: dict[str, NormalizedMatch] = {}
    for m in all_m:
        k = f"{m.date}:{m.home_team.lower()}:{m.away_team.lower()}"
        if k not in seen or m.status == "live":
            seen[k] = m

    status_o = {"live": 0, "upcoming": 1, "finished": 2}
    sorted_m = sorted(seen.values(), key=lambda m: (status_o.get(m.status, 9), m.start_time))
    output = [m.to_dict() for m in sorted_m]
    ttl = TTL["live"] if any(m.status == "live" for m in sorted_m) else TTL["today"]
    cache_set(f"basketball:{d}", output, ttl)
    logger.info(f"[basketball] {len(output)} matches for {d}")
    return output
