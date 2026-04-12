"""Normaliza dicts crudos de Promiedos → NormalizedMatch."""
import re
from scraping.models import NormalizedMatch
from scraping.argentina import detect_argentina_relevance, normalize_str


def normalize_match(raw: dict) -> NormalizedMatch | None:
    try:
        home = raw.get("home", "").strip()
        away = raw.get("away", "").strip()
        if not home or not away:
            return None

        competition = raw.get("competition", "Liga Profesional Argentina")
        status      = raw.get("status", "upcoming")
        home_score  = raw.get("home_score")
        away_score  = raw.get("away_score")
        minute      = raw.get("minute")
        start_time  = raw.get("start_time")

        relevance, arg_team = detect_argentina_relevance(home, away, competition, "futbol")

        home_n = re.sub(r"\W+", "-", normalize_str(home))[:20]
        away_n = re.sub(r"\W+", "-", normalize_str(away))[:20]

        return NormalizedMatch(
            id=f"futbol-promiedos-{home_n}-{away_n}",
            sport="futbol", source="promiedos",
            competition=competition,
            home_team=home, away_team=away,
            home_score=home_score, away_score=away_score,
            status=status, minute=minute,
            start_time_arg=start_time,
            argentina_relevance=relevance, argentina_team=arg_team,
            raw=raw,
        )
    except Exception:
        return None


def normalize_matches(raws: list[dict]) -> list[NormalizedMatch]:
    return [m for r in raws if (m := normalize_match(r)) is not None]
