"""
Normaliza datos crudos de Promiedos al formato NormalizedMatch.
"""
import re
from scraping.models import NormalizedMatch
from scraping.argentina import detect_argentina_relevance


def normalize_match(raw: dict) -> NormalizedMatch | None:
    """Convierte un dict crudo de Promiedos a NormalizedMatch."""
    try:
        home = raw.get("home", "").strip()
        away = raw.get("away", "").strip()
        if not home or not away:
            return None

        competition = raw.get("competition", "Liga Profesional Argentina")
        status = raw.get("status", "upcoming")
        home_score = raw.get("home_score")
        away_score = raw.get("away_score")
        minute = raw.get("minute")
        start_time = raw.get("start_time")

        relevance, arg_team = detect_argentina_relevance(home, away, competition, "futbol")

        home_slug = re.sub(r"\W+", "-", home.lower())[:20]
        away_slug = re.sub(r"\W+", "-", away.lower())[:20]

        return NormalizedMatch(
            id=f"futbol-promiedos-{home_slug}-{away_slug}",
            sport="futbol",
            source="promiedos",
            competition=competition,
            home_team=home,
            away_team=away,
            home_score=home_score,
            away_score=away_score,
            status=status,
            minute=minute,
            start_time_arg=start_time,
            argentina_relevance=relevance,
            argentina_team=arg_team,
            raw=raw,
        )
    except Exception:
        return None


def normalize_matches(raws: list[dict]) -> list[NormalizedMatch]:
    results = []
    for r in raws:
        m = normalize_match(r)
        if m:
            results.append(m)
    return results
