"""
Normaliza eventos JSON de Sofascore → NormalizedMatch.
"""
import re
import logging
from datetime import datetime, timezone
from scraping.models import NormalizedMatch
from scraping.argentina import detect_argentina_relevance

logger = logging.getLogger(__name__)

STATUS_MAP = {
    "notstarted": "upcoming", "inprogress": "live",
    "finished": "finished", "postponed": "finished",
    "canceled": "finished", "cancelled": "finished",
    "halftime": "live", "extra": "live", "penalties": "live",
    "interrupted": "live", "abandoned": "finished", "walkover": "finished",
}


def normalize_event(event: dict, sport: str) -> NormalizedMatch | None:
    try:
        home = event.get("homeTeam", {}).get("name", "").strip()
        away = event.get("awayTeam", {}).get("name", "").strip()
        if not home or not away:
            return None

        competition = (
            event.get("tournament", {}).get("name", "")
            or event.get("season", {}).get("name", "")
            or "—"
        ).strip()

        status_obj  = event.get("status", {})
        status_type = status_obj.get("type", "notstarted")
        status      = STATUS_MAP.get(status_type, "upcoming")

        # Scores
        home_score = away_score = None
        if status in ("live", "finished"):
            hs = event.get("homeScore", {})
            as_ = event.get("awayScore", {})
            raw_h = hs.get("current", hs.get("normaltime"))
            raw_a = as_.get("current", as_.get("normaltime"))
            try:
                home_score = int(raw_h) if raw_h is not None else None
            except (ValueError, TypeError):
                home_score = None
            try:
                away_score = int(raw_a) if raw_a is not None else None
            except (ValueError, TypeError):
                away_score = None

        # Minuto
        minute = None
        if status == "live":
            time_obj = event.get("time", {})
            played   = time_obj.get("played")
            extra    = time_obj.get("extra", 0) or 0
            if played is not None:
                minute = f"{played}+{extra}'" if extra > 0 else f"{played}'"
            else:
                desc = status_obj.get("description", "")
                if desc:
                    minute = desc

        # Datetime → hora ARG (UTC-3)
        dt_utc = start_time_arg = None
        ts = event.get("startTimestamp")
        if ts:
            try:
                dt_utc = datetime.fromtimestamp(int(ts), tz=timezone.utc)
                arg_h  = (dt_utc.hour - 3) % 24
                start_time_arg = f"{arg_h:02d}:{dt_utc.minute:02d}"
            except (ValueError, OSError):
                pass

        relevance, arg_team = detect_argentina_relevance(home, away, competition, sport)

        event_id  = event.get("id", "0")
        home_slug = re.sub(r"\W+", "-", home.lower())[:20]
        away_slug = re.sub(r"\W+", "-", away.lower())[:20]

        return NormalizedMatch(
            id=f"{sport}-ss-{event_id}",
            sport=sport, source="sofascore",
            competition=competition,
            competition_id=str(event.get("tournament", {}).get("id", "")),
            home_team=home, away_team=away,
            home_team_id=str(event.get("homeTeam", {}).get("id", "")),
            away_team_id=str(event.get("awayTeam", {}).get("id", "")),
            home_score=home_score, away_score=away_score,
            status=status, minute=minute,
            datetime_utc=dt_utc, start_time_arg=start_time_arg,
            argentina_relevance=relevance, argentina_team=arg_team,
            raw=event,
        )
    except Exception as e:
        logger.debug(f"[ss_norm] error: {e}")
        return None


def normalize_events(events: list[dict], sport: str) -> list[NormalizedMatch]:
    """Normaliza y filtra solo los con relevancia argentina."""
    results, skipped = [], 0
    for e in events:
        m = normalize_event(e, sport)
        if m and m.argentina_relevance != "none":
            results.append(m)
        else:
            skipped += 1
    logger.debug(
        f"[ss_norm] {sport}: {len(results)} ARG, {skipped} descartados "
        f"de {len(events)} total"
    )
    return results


def normalize_events_all(events: list[dict], sport: str) -> list[NormalizedMatch]:
    """Sin filtro de argentina — para debug."""
    return [m for e in events if (m := normalize_event(e, sport)) is not None]
