"""
hockey.py — Scraper de hockey sobre césped para El Tablón Albiceleste
Fuentes: Sofascore (field-hockey) → FIH data
"""

import asyncio
import logging
from .api_sports_base import (
    NormalizedMatch, fetch_json,
    today_art, time_art, date_art,
    cache_get, cache_set, TTL,
)

logger = logging.getLogger("tablon.hockey")

_SOFA_HEADERS = {"Referer": "https://www.sofascore.com/"}

_ARG_HOCKEY_KEYWORDS = {
    "argentina", "las leonas", "los leones",
    "geba", "banco nacion", "banco nación",
    "casi", "lomas", "san fernando", "la plata",
    "atletico", "hindú", "hindu", "regatas",
}

def _is_arg_hockey(home: str, away: str, comp: str) -> bool:
    text = f"{home} {away} {comp}".lower()
    return any(k in text for k in _ARG_HOCKEY_KEYWORDS)

async def _sofa_hockey(date: str) -> list[NormalizedMatch]:
    # Sofascore usa "field-hockey" para hockey sobre cesped
    url = f"https://api.sofascore.com/api/v1/sport/field-hockey/scheduled-events/{date}"
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

            if country != "Argentina" and not _is_arg_hockey(home, away, comp):
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
                sport="hockey",
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
            logger.debug(f"[sofa_hockey] {e}")
    return results

async def get_hockey_today(date: str | None = None) -> list[dict]:
    d = date or today_art()
    cached = cache_get(f"hockey:{d}")
    if cached is not None:
        return cached

    matches = await _sofa_hockey(d)
    status_o = {"live": 0, "upcoming": 1, "finished": 2}
    sorted_m = sorted(matches, key=lambda m: (status_o.get(m.status, 9), m.start_time))
    output = [m.to_dict() for m in sorted_m]
    cache_set(f"hockey:{d}", output, TTL["today"])
    logger.info(f"[hockey] {len(output)} matches for {d}")
    return output
