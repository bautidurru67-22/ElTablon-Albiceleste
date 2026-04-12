"""
volleyball.py — Vóley para El Tablón Albiceleste
Fuentes: Sofascore → Volleybox (fallback)
"""
import logging
from .api_sports_base import (
    NormalizedMatch, fetch_json,
    today_art, time_art, date_art,
    cache_get, cache_set, TTL,
)

logger = logging.getLogger("tablon.volleyball")
_SOFA_HEADERS = {"Referer": "https://www.sofascore.com/"}

_ARG_VOL_KW = {
    "argentina", "las panteras", "upcn", "lava jato",
    "river", "boca", "lomas", "ciudad vóley", "personal",
}

def _is_arg_vol(home: str, away: str, comp: str, country: str) -> bool:
    if country == "Argentina":
        return True
    text = f"{home} {away} {comp}".lower()
    return any(k in text for k in _ARG_VOL_KW)

async def get_volleyball_today(date: str | None = None) -> list[dict]:
    d = date or today_art()
    cached = cache_get(f"volleyball:{d}")
    if cached is not None:
        return cached

    url = f"https://api.sofascore.com/api/v1/sport/volleyball/scheduled-events/{d}"
    data = await fetch_json(url, headers=_SOFA_HEADERS)
    if not data:
        cache_set(f"volleyball:{d}", [], TTL["error"])
        return []

    results = []
    for ev in data.get("events", []):
        try:
            home = ev.get("homeTeam", {}).get("name", "")
            away = ev.get("awayTeam", {}).get("name", "")
            comp = ev.get("tournament", {}).get("name", "")
            country = ev.get("tournament", {}).get("category", {}).get("country", {}).get("name", "")
            if not _is_arg_vol(home, away, comp, country):
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

            # Sets
            home_score = ev.get("homeScore", {}).get("current")
            away_score = ev.get("awayScore", {}).get("current")
            period = ev.get("lastPeriod", "")
            sets = []
            for i in range(1, 6):
                h = ev.get("homeScore", {}).get(f"period{i}")
                a = ev.get("awayScore", {}).get(f"period{i}")
                if h is not None:
                    sets.append(f"{h}-{a}")

            results.append(NormalizedMatch(
                sport="voley",
                competition=comp,
                home_team=home,
                away_team=away,
                home_score=home_score,
                away_score=away_score,
                status=_map.get(status_raw, "upcoming"),
                start_time=time_art(start_iso),
                date=match_date,
                period=f"Set {len(sets)}" if sets else period,
                minute=" | ".join(sets) if sets else None,
                argentina_relevance="seleccion" if "argentina" in f"{home}{away}".lower() else "club_arg",
                source="sofascore",
                match_id=str(ev.get("id", "")),
            ))
        except Exception as e:
            logger.debug(f"[volleyball] {e}")

    status_o = {"live": 0, "upcoming": 1, "finished": 2}
    output = [m.to_dict() for m in sorted(results, key=lambda m: (status_o.get(m.status, 9), m.start_time))]
    cache_set(f"volleyball:{d}", output, TTL["today"])
    logger.info(f"[volleyball] {len(output)} matches for {d}")
    return output
