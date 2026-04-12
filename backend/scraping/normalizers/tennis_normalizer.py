"""
Normaliza datos de tenis (ATP/WTA/Challenger) al formato NormalizedMatch.
Maneja el formato de puntaje particular del tenis: sets, games, tie-breaks.
"""
import re
from scraping.models import NormalizedMatch
from scraping.argentina import detect_argentina_relevance, ARG_PLAYERS


def parse_tennis_score(score_raw: str) -> tuple[int | None, int | None, str | None]:
    """
    Parsea un score de tenis tipo "6-4 7-5" o "6-3 3-6 7-6(4)".
    Retorna (sets_player1, sets_player2, score_detail).
    """
    if not score_raw:
        return None, None, None

    score_raw = score_raw.strip()
    sets = re.findall(r'(\d+)-(\d+)(?:\(\d+\))?', score_raw)
    if not sets:
        return None, None, score_raw

    p1_sets = sum(1 for a, b in sets if int(a) > int(b))
    p2_sets = sum(1 for a, b in sets if int(b) > int(a))

    return p1_sets, p2_sets, score_raw


def normalize_atp_raw(raw: dict) -> NormalizedMatch | None:
    """
    Convierte un dict crudo de ATP (parseado de HTML o Sofascore) a NormalizedMatch.
    Esperado:
      player1, player2, score_raw, status, competition, start_time
    """
    try:
        p1 = raw.get("player1", "").strip()
        p2 = raw.get("player2", "").strip()
        if not p1 or not p2:
            return None

        competition = raw.get("competition", "ATP Tour")
        score_raw = raw.get("score_raw", "")
        status = raw.get("status", "upcoming")
        start_time = raw.get("start_time")
        minute = raw.get("minute")

        sets_p1, sets_p2, score_detail = parse_tennis_score(score_raw)

        relevance, arg_team = detect_argentina_relevance(p1, p2, competition, "tenis")

        p1_slug = re.sub(r"\W+", "-", p1.lower())[:20]
        p2_slug = re.sub(r"\W+", "-", p2.lower())[:20]

        return NormalizedMatch(
            id=f"tenis-atp-{p1_slug}-{p2_slug}",
            sport="tenis",
            source=raw.get("source", "atptour"),
            competition=competition,
            home_team=p1,
            away_team=p2,
            home_score=sets_p1,
            away_score=sets_p2,
            score_detail=score_detail,
            status=status,
            minute=minute or (score_raw if status == "live" else None),
            start_time_arg=start_time,
            argentina_relevance=relevance,
            argentina_team=arg_team,
            raw=raw,
        )
    except Exception:
        return None


def normalize_matches(raws: list[dict]) -> list[NormalizedMatch]:
    return [m for raw in raws if (m := normalize_atp_raw(raw)) is not None]
