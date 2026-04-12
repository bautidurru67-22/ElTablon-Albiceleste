"""
futsal.py — Futsal para El Tablón Albiceleste
Fuentes: Sofascore → AFA Futsal (fallback)
"""
import logging
from .api_sports_base import (
    NormalizedMatch, fetch_json,
    today_art, time_art, date_art,
    cache_get, cache_set, TTL,
)

logger = logging.getLogger("tablon.futsal")
_SOFA_HEADERS = {"Referer": "https://www.sofascore.com/"}

async def get_futsal_today(date: str | None = None) -> list[dict]:
    d = date or today_art()
    cached = cache_get(f"futsal:{d}")
    if cached is not None:
        return cached

    url = f"https://api.sofascore.com/api/v1/sport/futsal/scheduled-events/{d}"
    data = await fetch_json(url, headers=_SOFA_HEADERS)
    if not data:
        cache_set(f"futsal:{d}", [], TTL["error"])
        return []

    results = []
    for ev in data.get("events", []):
        try:
            home = ev.get("homeTeam", {}).get("name", "")
            away = ev.get("awayTeam", {}).get("name", "")
            comp = ev.get("tournament", {}).get("name", "")
            country = ev.get("tournament", {}).get("category", {}).get("country", {}).get("name", "")

            is_arg = (
                country == "Argentina" or
                "argentina" in f"{home} {away}".lower()
            )
            if not is_arg:
                continue

            ts = ev.get("startTimestamp", 0)
            from datetime import datetime, timezone as tz_
            dt = datetime.fromtimestamp(ts, tz=tz_.utc)
            start_iso = dt.isoformat()
            match_date = date_art(start_iso)
            if match_date != d:
                continue

            status_raw = ev.get("status", {}).get("type", "notstarted")
            _map = {"notstarted": "upcoming", "inprogress": "live", "finished": "finished"}

            results.append(NormalizedMatch(
                sport="futsal",
                competition=comp,
                home_team=home,
                away_team=away,
                home_score=ev.get("homeScore", {}).get("current"),
                away_score=ev.get("awayScore", {}).get("current"),
                status=_map.get(status_raw, "upcoming"),
                start_time=time_art(start_iso),
                date=match_date,
                argentina_relevance="seleccion" if "argentina" in f"{home}{away}".lower() else "club_arg",
                source="sofascore",
                match_id=str(ev.get("id", "")),
            ))
        except Exception as e:
            logger.debug(f"[futsal] {e}")

    status_o = {"live": 0, "upcoming": 1, "finished": 2}
    output = [m.to_dict() for m in sorted(results, key=lambda m: (status_o.get(m.status, 9), m.start_time))]
    cache_set(f"futsal:{d}", output, TTL["today"])
    logger.info(f"[futsal] {len(output)} matches for {d}")
    return output
