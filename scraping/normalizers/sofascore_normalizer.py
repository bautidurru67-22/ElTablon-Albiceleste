"""
Normaliza eventos de la API de Sofascore al formato NormalizedMatch.
"""
from datetime import datetime, timezone
from scraping.models import NormalizedMatch
from scraping.argentina import detect_argentina_relevance
import re

STATUS_MAP = {
    "notstarted": "upcoming",
    "inprogress": "live",
    "finished": "finished",
    "postponed": "finished",
    "canceled": "finished",
    "halftime": "live",
}


def normalize_event(event: dict, sport: str) -> NormalizedMatch | None:
    """Convierte un evento crudo de Sofascore a NormalizedMatch."""
    try:
        home = event.get("homeTeam", {}).get("name", "")
        away = event.get("awayTeam", {}).get("name", "")
        competition = (
            event.get("tournament", {}).get("name", "")
            or event.get("season", {}).get("name", "")
        )

        status_raw = event.get("status", {}).get("type", "notstarted")
        status = STATUS_MAP.get(status_raw, "upcoming")

        home_score = None
        away_score = None
        if status in ("live", "finished"):
            scores = event.get("homeScore", {})
            home_score = scores.get("current") or scores.get("normaltime")
            scores = event.get("awayScore", {})
            away_score = scores.get("current") or scores.get("normaltime")

        minute = None
        if status == "live":
            minute_raw = event.get("time", {}).get("played")
            if minute_raw is not None:
                minute = f"{minute_raw}'"

        dt_utc = None
        start_time_arg = None
        ts = event.get("startTimestamp")
        if ts:
            dt_utc = datetime.fromtimestamp(ts, tz=timezone.utc)
            # Argentina = UTC-3
            arg_hour = (dt_utc.hour - 3) % 24
            start_time_arg = f"{arg_hour:02d}:{dt_utc.minute:02d}"

        relevance, arg_team = detect_argentina_relevance(home, away, competition, sport)

        event_id = event.get("id", "")
        home_slug = re.sub(r"\W+", "-", home.lower())[:20]
        away_slug = re.sub(r"\W+", "-", away.lower())[:20]

        return NormalizedMatch(
            id=f"{sport}-sofascore-{event_id}",
            sport=sport,
            source="sofascore",
            competition=competition,
            competition_id=str(event.get("tournament", {}).get("id", "")),
            home_team=home,
            away_team=away,
            home_team_id=str(event.get("homeTeam", {}).get("id", "")),
            away_team_id=str(event.get("awayTeam", {}).get("id", "")),
            home_score=home_score,
            away_score=away_score,
            status=status,
            minute=minute,
            datetime_utc=dt_utc,
            start_time_arg=start_time_arg,
            argentina_relevance=relevance,
            argentina_team=arg_team,
            raw=event,
        )
    except Exception:
        return None


def normalize_events(events: list[dict], sport: str) -> list[NormalizedMatch]:
    results = []
    for e in events:
        m = normalize_event(e, sport)
        if m and m.argentina_relevance != "none":
            results.append(m)
    return results
