"""
tennis.py — Scraper de tenis para El Tablón Albiceleste
Fuentes: Sofascore (principal) → LiveScore → ESPN ATP/WTA
Detecta automáticamente jugadores argentinos.
"""

import asyncio
import logging
from .api_sports_base import (
    NormalizedMatch, fetch_json,
    today_art, time_art, date_art,
    cache_get, cache_set, TTL,
)

logger = logging.getLogger("tablon.tennis")

_SOFA_HEADERS = {"Referer": "https://www.sofascore.com/"}

# Jugadores argentinos (normalizado lowercase sin tildes)
_ARG_PLAYERS = {
    "cerundolo", "cerúndolo", "francisco cerundolo",
    "etcheverry", "tomas etcheverry", "tomás etcheverry",
    "baez", "báez", "sebastian baez",
    "navone", "mariano navone",
    "bagnis", "facundo bagnis",
    "cachin", "pedro cachin",
    "ficovich", "juan pablo ficovich",
    "ugo carabelli", "camilo ugo carabelli",
    "delbonis", "federico delbonis",
    "zeballos", "horacio zeballos",
    "gonzalez", "maximo gonzalez",
    "podoroska", "nadia podoroska",
    "sierra", "solana sierra",
    "riera", "julia riera",
    "carle", "lourdes carle",
    "collarini", "andrea collarini",
    "burruchaga",
    "trungelliti",
}

def _is_arg_tennis(home: str, away: str) -> bool:
    text = f"{home} {away}".lower()
    import unicodedata
    text = "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )
    return any(p in text for p in _ARG_PLAYERS)

def _tennis_relevance(home: str, away: str) -> tuple[str, str | None]:
    if _is_arg_tennis(home, away):
        return "jugador_arg", None
    return "none", None

# ─── SOFASCORE ───────────────────────────────────────────────
async def _sofa_tennis(date: str) -> list[NormalizedMatch]:
    url = f"https://api.sofascore.com/api/v1/sport/tennis/scheduled-events/{date}"
    data = await fetch_json(url, headers=_SOFA_HEADERS)
    if not data or "events" not in data:
        return []

    results = []
    for ev in data["events"]:
        try:
            home = ev.get("homeTeam", {}).get("name", "")
            away = ev.get("awayTeam", {}).get("name", "")
            if not home or not away:
                continue

            relevance, arg_team = _tennis_relevance(home, away)
            # For tennis we include ALL matches if any arg player involved
            # but also include non-arg for context

            comp = ev.get("tournament", {}).get("name", "")
            cat  = ev.get("tournament", {}).get("category", {}).get("name", "")
            competition = f"{cat} · {comp}" if cat else comp

            status_raw = ev.get("status", {}).get("type", "notstarted")
            _map = {"notstarted": "upcoming", "inprogress": "live", "finished": "finished"}
            status = _map.get(status_raw, "upcoming")

            ts = ev.get("startTimestamp", 0)
            from datetime import datetime, timezone as tz_
            dt = datetime.fromtimestamp(ts, tz=tz_.utc)
            start_iso = dt.isoformat()
            match_date = date_art(start_iso)
            if match_date != date:
                continue

            start_time = time_art(start_iso)

            # Scores (tenis — sets)
            home_score = ev.get("homeScore", {}).get("current")
            away_score = ev.get("awayScore", {}).get("current")

            # Build set detail
            sets_home = []
            sets_away = []
            for i in range(1, 6):
                h = ev.get("homeScore", {}).get(f"period{i}")
                a = ev.get("awayScore", {}).get(f"period{i}")
                if h is not None and a is not None:
                    sets_home.append(str(h))
                    sets_away.append(str(a))

            period = None
            minute = None
            if status == "live" and sets_home:
                period = f"{len(sets_home)}er set"

            results.append(NormalizedMatch(
                sport="tenis",
                competition=competition,
                home_team=home,
                away_team=away,
                home_score=home_score,
                away_score=away_score,
                status=status,
                start_time=start_time,
                date=match_date,
                minute=" ".join(sets_home) if sets_home else minute,
                period=period,
                argentina_relevance=relevance,
                argentina_team=arg_team,
                source="sofascore",
                match_id=str(ev.get("id", "")),
            ))
        except Exception as e:
            logger.debug(f"[sofa_tennis] parse: {e}")

    return results

# ─── ESPN ATP/WTA ─────────────────────────────────────────────
async def _espn_tennis(date: str) -> list[NormalizedMatch]:
    results = []
    date_str = date.replace("-", "")
    for tour in ("atp.singles", "wta.singles"):
        url = (
            f"https://site.api.espn.com/apis/site/v2/sports/tennis/"
            f"{tour}/scoreboard?dates={date_str}&limit=50"
        )
        data = await fetch_json(url)
        if not data:
            continue
        for ev in data.get("events", []):
            try:
                comp_obj = ev.get("competitions", [{}])[0]
                competitors = comp_obj.get("competitors", [])
                if len(competitors) < 2:
                    continue

                home = competitors[0].get("athlete", {}).get("displayName", "")
                away = competitors[1].get("athlete", {}).get("displayName", "")
                if not home or not away:
                    continue

                relevance, _ = _tennis_relevance(home, away)
                if relevance == "none":
                    continue  # Tennis: only include if ARG player

                status_type = comp_obj.get("status", {}).get("type", {}).get("name", "")
                status = "live" if "IN" in status_type else ("finished" if "FINAL" in status_type else "upcoming")

                start_iso = comp_obj.get("date", "")
                match_date = date_art(start_iso) if start_iso else date
                if match_date != date:
                    continue

                comp_name = ev.get("name", tour.upper())

                results.append(NormalizedMatch(
                    sport="tenis",
                    competition=comp_name,
                    home_team=home,
                    away_team=away,
                    home_score=None,
                    away_score=None,
                    status=status,
                    start_time=time_art(start_iso) if start_iso else "--:--",
                    date=match_date,
                    argentina_relevance=relevance,
                    argentina_team=None,
                    source="espn",
                    match_id=str(ev.get("id", "")),
                ))
            except Exception as e:
                logger.debug(f"[espn_tennis] parse: {e}")
    return results

# ─── DEDUP ───────────────────────────────────────────────────
def _norm_player(name: str) -> str:
    import unicodedata, re
    n = unicodedata.normalize("NFD", name.lower())
    n = "".join(c for c in n if unicodedata.category(c) != "Mn")
    # Keep only last name (for "F. Cerundolo" vs "Francisco Cerundolo")
    parts = re.sub(r"[^a-z\s]", "", n).split()
    return parts[-1] if parts else n

def _dedup_tennis(matches: list[NormalizedMatch]) -> list[NormalizedMatch]:
    seen: dict[str, NormalizedMatch] = {}
    prio = {"sofascore": 2, "espn": 1}
    for m in matches:
        p1 = _norm_player(m.home_team)
        p2 = _norm_player(m.away_team)
        key = f"{m.date}:{':'.join(sorted([p1, p2]))}"
        if key not in seen:
            seen[key] = m
        elif prio.get(m.source, 0) > prio.get(seen[key].source, 0):
            seen[key] = m
    return list(seen.values())

# ─── PUNTO DE ENTRADA ────────────────────────────────────────
async def get_tennis_today(date: str | None = None) -> list[dict]:
    """
    Retorna partidos de tenis del día con jugadores argentinos.
    """
    d = date or today_art()
    cache_key = f"tennis:{d}"

    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    logger.info(f"[tennis] Fetching for {d}")

    sofa, espn = await asyncio.gather(
        _sofa_tennis(d),
        _espn_tennis(d),
        return_exceptions=True,
    )

    all_matches: list[NormalizedMatch] = []
    if not isinstance(sofa, Exception):
        all_matches.extend(sofa)
        logger.info(f"[tennis] sofascore: {len(sofa)} matches")
    if not isinstance(espn, Exception):
        all_matches.extend(espn)
        logger.info(f"[tennis] espn: {len(espn)} matches")

    # Filter: only include matches with arg players
    arg_matches = [m for m in all_matches if m.argentina_relevance != "none"]
    deduped = _dedup_tennis(arg_matches)

    status_order = {"live": 0, "upcoming": 1, "finished": 2}
    sorted_matches = sorted(deduped, key=lambda m: (status_order.get(m.status, 9), m.start_time))

    output = [m.to_dict() for m in sorted_matches]
    ttl = TTL["live"] if any(m.status == "live" for m in sorted_matches) else TTL["today"]
    cache_set(cache_key, output, ttl)

    logger.info(f"[tennis] Total: {len(output)} ARG-relevant matches for {d}")
    return output
