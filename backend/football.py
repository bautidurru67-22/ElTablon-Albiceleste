"""
football.py — Scraper de fútbol para El Tablón Albiceleste
Fuentes en cascada:
  1. Sofascore (principal — sin auth)
  2. ESPN undocumented API (sin auth)
  3. Fotmob (sin auth)
  4. TheSportsDB (sin auth, key="3")
"""

import logging
from typing import Optional
from .api_sports_base import (
    NormalizedMatch, fetch_json, today_art, time_art, date_art,
    cache_get, cache_set, TTL, detect_argentina_relevance,
)

logger = logging.getLogger("tablon.football")

# ─── SOFASCORE ───────────────────────────────────────────────
_SOFA_HEADERS = {
    "Referer": "https://www.sofascore.com/",
    "Origin": "https://www.sofascore.com",
}

_SOFA_STATUS = {
    "notstarted": "upcoming",
    "inprogress":  "live",
    "finished":    "finished",
    "postponed":   "upcoming",
    "canceled":    "finished",
}

async def _sofa_football(date: str) -> list[NormalizedMatch]:
    url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{date}"
    data = await fetch_json(url, headers=_SOFA_HEADERS)
    if not data or "events" not in data:
        return []

    results = []
    for ev in data["events"]:
        try:
            home = ev.get("homeTeam", {}).get("name", "")
            away = ev.get("awayTeam", {}).get("name", "")
            comp = ev.get("tournament", {}).get("name", "")
            country = ev.get("tournament", {}).get("category", {}).get("country", {}).get("name", "")

            status_raw = ev.get("status", {}).get("type", "notstarted")
            status = _SOFA_STATUS.get(status_raw, "upcoming")

            ts = ev.get("startTimestamp", 0)
            from datetime import datetime, timezone
            dt_utc = datetime.fromtimestamp(ts, tz=timezone.utc)
            start_iso = dt_utc.isoformat()
            match_date = date_art(start_iso)
            start_time = time_art(start_iso)

            # Only process if date matches
            if match_date != date:
                continue

            home_score = ev.get("homeScore", {}).get("current")
            away_score = ev.get("awayScore", {}).get("current")

            minute = None
            period = None
            if status == "live":
                elapsed = ev.get("time", {}).get("currentPeriodStartTimestamp")
                if elapsed:
                    import time as _time
                    mins = int((_time.time() - elapsed) / 60)
                    minute = f"{mins}'"
                period = ev.get("lastPeriod", "")

            relevance, arg_team = detect_argentina_relevance(home, away, comp)

            tid_home = ev.get("homeTeam", {}).get("id")
            tid_away = ev.get("awayTeam", {}).get("id")

            results.append(NormalizedMatch(
                sport="futbol",
                competition=comp,
                home_team=home,
                away_team=away,
                home_score=home_score,
                away_score=away_score,
                status=status,
                start_time=start_time,
                date=match_date,
                minute=minute,
                period=period,
                argentina_relevance=relevance,
                argentina_team=arg_team,
                source="sofascore",
                home_logo=f"https://api.sofascore.com/api/v1/team/{tid_home}/image" if tid_home else None,
                away_logo=f"https://api.sofascore.com/api/v1/team/{tid_away}/image" if tid_away else None,
                match_id=str(ev.get("id", "")),
            ))
        except Exception as e:
            logger.debug(f"[sofa_football] parse error: {e}")

    return results

# ─── ESPN ────────────────────────────────────────────────────
_ESPN_LEAGUES = [
    ("arg.1",                    "Liga Profesional Argentina"),
    ("arg.2",                    "Primera Nacional"),
    ("conmebol.libertadores",    "Copa Libertadores"),
    ("conmebol.sudamericana",    "Copa Sudamericana"),
    ("arg.copa",                 "Copa Argentina"),
]

async def _espn_football(date: str) -> list[NormalizedMatch]:
    results = []
    date_str = date.replace("-", "")

    for league_id, league_name in _ESPN_LEAGUES:
        url = (
            f"https://site.api.espn.com/apis/site/v2/sports/soccer/"
            f"{league_id}/scoreboard?dates={date_str}&limit=50&lang=es&region=ar"
        )
        data = await fetch_json(url)
        if not data or "events" not in data:
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

                status_type = comp_obj.get("status", {}).get("type", {}).get("name", "STATUS_SCHEDULED")
                if "IN" in status_type or "PROGRESS" in status_type:
                    status = "live"
                elif "FINAL" in status_type or "POST" in status_type:
                    status = "finished"
                else:
                    status = "upcoming"

                start_iso = comp_obj.get("date", "")
                start_time = time_art(start_iso) if start_iso else "--:--"
                match_date = date_art(start_iso) if start_iso else date

                if match_date != date:
                    continue

                home_score_raw = home_c.get("score")
                away_score_raw = away_c.get("score")
                home_score = int(home_score_raw) if home_score_raw is not None else None
                away_score = int(away_score_raw) if away_score_raw is not None else None

                minute = None
                period = None
                if status == "live":
                    clock = comp_obj.get("status", {}).get("displayClock", "")
                    period_num = comp_obj.get("status", {}).get("period", 0)
                    minute = clock if clock else None
                    period = f"{period_num}T" if period_num else None

                relevance, arg_team = detect_argentina_relevance(home, away, league_name)

                results.append(NormalizedMatch(
                    sport="futbol",
                    competition=league_name,
                    home_team=home,
                    away_team=away,
                    home_score=home_score,
                    away_score=away_score,
                    status=status,
                    start_time=start_time,
                    date=match_date,
                    minute=minute,
                    period=period,
                    argentina_relevance=relevance,
                    argentina_team=arg_team,
                    source="espn",
                    home_logo=home_c.get("team", {}).get("logo"),
                    away_logo=away_c.get("team", {}).get("logo"),
                    match_id=str(ev.get("id", "")),
                ))
            except Exception as e:
                logger.debug(f"[espn_football] parse error: {e}")

    return results

# ─── FOTMOB ──────────────────────────────────────────────────
_FOTMOB_ARG_LEAGUE_IDS = {112, 121, 395, 266, 267}

async def _fotmob_football(date: str) -> list[NormalizedMatch]:
    date_str = date.replace("-", "")
    url = f"https://www.fotmob.com/api/matches?date={date_str}"
    data = await fetch_json(url, headers={"Referer": "https://www.fotmob.com/"})
    if not data or "leagues" not in data:
        return []

    results = []
    for league in data.get("leagues", []):
        league_id = league.get("id", 0)
        country = league.get("ccode", "")
        league_name = league.get("name", "")

        if country != "ARG" and league_id not in _FOTMOB_ARG_LEAGUE_IDS:
            continue

        for match in league.get("matches", []):
            try:
                home = match.get("home", {}).get("name", "")
                away = match.get("away", {}).get("name", "")
                if not home or not away:
                    continue

                st = match.get("status", {})
                started  = st.get("started", False)
                finished = st.get("finished", False)

                if finished:
                    status = "finished"
                elif started:
                    status = "live"
                else:
                    status = "upcoming"

                match_time = match.get("time", "--:--")[:5]

                home_score = match.get("home", {}).get("score")
                away_score = match.get("away", {}).get("score")
                try:
                    home_score = int(home_score) if home_score is not None else None
                    away_score = int(away_score) if away_score is not None else None
                except (TypeError, ValueError):
                    home_score = away_score = None

                minute = None
                if status == "live":
                    live_time = st.get("liveTime", {})
                    minute = live_time.get("short", "")

                relevance, arg_team = detect_argentina_relevance(home, away, league_name)
                h_id = match.get("home", {}).get("id")
                a_id = match.get("away", {}).get("id")

                results.append(NormalizedMatch(
                    sport="futbol",
                    competition=league_name,
                    home_team=home,
                    away_team=away,
                    home_score=home_score,
                    away_score=away_score,
                    status=status,
                    start_time=match_time,
                    date=date,
                    minute=minute,
                    argentina_relevance=relevance,
                    argentina_team=arg_team,
                    source="fotmob",
                    home_logo=f"https://images.fotmob.com/image_resources/logo/teamlogo/{h_id}.png" if h_id else None,
                    away_logo=f"https://images.fotmob.com/image_resources/logo/teamlogo/{a_id}.png" if a_id else None,
                    match_id=str(match.get("id", "")),
                ))
            except Exception as e:
                logger.debug(f"[fotmob] parse error: {e}")

    return results

# ─── DEDUPLICACIÓN ───────────────────────────────────────────
def _dedup(matches: list[NormalizedMatch]) -> list[NormalizedMatch]:
    """Elimina duplicados, prefiere la versión con mayor info."""
    seen: dict[str, NormalizedMatch] = {}
    priority = {"espn": 3, "fotmob": 2, "sofascore": 1}
    status_prio = {"live": 0, "upcoming": 1, "finished": 2}

    for m in matches:
        key = f"{m.date}:{_norm(m.home_team)}:{_norm(m.away_team)}"
        if key not in seen:
            seen[key] = m
        else:
            existing = seen[key]
            # Prefer better status then higher source priority
            if status_prio.get(m.status, 9) < status_prio.get(existing.status, 9):
                seen[key] = m
            elif (m.status == existing.status and
                  priority.get(m.source, 0) > priority.get(existing.source, 0)):
                seen[key] = {**existing.__dict__, **{
                    k: v for k, v in m.__dict__.items()
                    if v is not None and k not in ("source",)
                }}
                seen[key] = NormalizedMatch(**seen[key])
    return list(seen.values())

def _norm(name: str) -> str:
    import unicodedata, re
    n = unicodedata.normalize("NFD", name.lower())
    n = "".join(c for c in n if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", n)

# ─── FILTRO ARG ──────────────────────────────────────────────
_ARG_KEYWORDS = {
    "argentina", "liga profesional", "primera nacional",
    "copa argentina", "libertadores", "sudamericana",
    "torneo", "ascenso", "federal",
}

def _is_arg_relevant(m: NormalizedMatch) -> bool:
    if m.argentina_relevance in ("seleccion", "club_arg", "jugador_arg"):
        return True
    comp_l = m.competition.lower()
    return any(kw in comp_l for kw in _ARG_KEYWORDS)

# ─── PUNTO DE ENTRADA PRINCIPAL ──────────────────────────────
async def get_football_today(date: str | None = None) -> list[dict]:
    """
    Retorna partidos de fútbol relevantes para Argentina hoy.
    Cascade: Sofascore → ESPN → Fotmob
    Con caché de 90 segundos.
    """
    d = date or today_art()
    cache_key = f"football:{d}"

    cached = cache_get(cache_key)
    if cached is not None:
        return cached

    logger.info(f"[football] Fetching for {d}")

    # Fetch todas las fuentes en paralelo
    import asyncio
    results_per_source = await asyncio.gather(
        _sofa_football(d),
        _espn_football(d),
        _fotmob_football(d),
        return_exceptions=True,
    )

    all_matches: list[NormalizedMatch] = []
    source_names = ["sofascore", "espn", "fotmob"]
    for name, result in zip(source_names, results_per_source):
        if isinstance(result, Exception):
            logger.error(f"[football] {name} failed: {result}")
        elif isinstance(result, list):
            logger.info(f"[football] {name}: {len(result)} matches")
            all_matches.extend(result)

    # Filtrar, deduplicar, ordenar
    arg_matches = [m for m in all_matches if _is_arg_relevant(m)]
    deduped = _dedup(arg_matches)

    status_order = {"live": 0, "upcoming": 1, "finished": 2}
    sorted_matches = sorted(
        deduped,
        key=lambda m: (status_order.get(m.status, 9), m.start_time)
    )

    output = [m.to_dict() for m in sorted_matches]
    ttl = TTL["live"] if any(m.status == "live" for m in sorted_matches) else TTL["today"]
    cache_set(cache_key, output, ttl)

    logger.info(f"[football] Total: {len(output)} matches for {d}")
    return output
