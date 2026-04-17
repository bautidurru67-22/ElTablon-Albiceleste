"""
api_hoy.py — Endpoints agregados para El Tablón Albiceleste

Reglas:
- SIEMPRE usa ART (UTC-3)
- /hoy, /resultados, /live y /calendario leen cache central (hoy:all + today:*)
- Nunca bloquea request con scraping sincrónico
- Ranking editorial fino y extensible a multideporte:
    1) Selección Argentina
    2) Fútbol argentino de máxima jerarquía
    3) Copas internacionales con clubes argentinos
    4) Otros deportes argentinos relevantes
    5) Argentinos en el exterior
    6) Motorsport argentino
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from api_sports_base import now_art, today_art
from app.cache import cache
from app.config import settings
from app.models.match import Match

router = APIRouter(tags=["hoy"])


# ─────────────────────────────────────────────────────────────────────────────
# Helpers base
# ─────────────────────────────────────────────────────────────────────────────

BIG_ARG_CLUBS = {
    "boca",
    "boca juniors",
    "river",
    "river plate",
    "racing",
    "racing club",
    "independiente",
    "san lorenzo",
    "newells",
    "newell's",
    "newells old boys",
    "newell's old boys",
    "rosario central",
    "talleres",
    "velez",
    "velez sarsfield",
    "estudiantes",
}

MID_ARG_CLUBS = {
    "union",
    "union santa fe",
    "union de santa fe",
    "lanus",
    "huracan",
    "gimnasia",
    "gimnasia la plata",
    "platense",
    "belgrano",
    "instituto",
    "defensa y justicia",
    "argentinos juniors",
    "banfield",
    "sarmiento",
    "tigre",
    "godoy cruz",
    "central cordoba",
    "aldosivi",
    "quilmes",
    "chacarita",
    "ferro",
    "patronato",
    "temperley",
    "all boys",
    "nueva chicago",
    "arsenal sarandi",
    "arsenal de sarandi",
    "excursionistas",
}

TOP_FOOTBALL_COMPETITIONS = {
    "liga profesional",
    "liga profesional de futbol",
    "liga profesional de fútbol",
    "torneo betano",
}

SECOND_TIER_FOOTBALL_COMPETITIONS = {
    "primera nacional",
    "primera b",
    "b metro",
    "federal a",
    "primera c",
    "primera d",
    "reserva",
    "femenina",
    "primera femenina",
}

CUP_FOOTBALL_COMPETITIONS = {
    "copa argentina",
    "copa de la liga",
    "supercopa argentina",
    "trofeo de campeones",
}

CONMEBOL_COMPETITIONS = {
    "libertadores",
    "sudamericana",
    "recopa",
    "conmebol",
}

TOP_EXTERIOR_COMPETITIONS = {
    "premier league",
    "la liga",
    "serie a",
    "bundesliga",
    "ligue 1",
    "champions league",
    "europa league",
    "conference league",
}

OTHER_SPORT_PREMIUM_HINTS = {
    "basquet": [
        "liga nacional",
        "liga argentina",
        "selección argentina",
        "seleccion argentina",
        "fiba",
    ],
    "tenis": [
        "atp",
        "wta",
        "challenger",
        "copa davis",
        "billie jean king cup",
    ],
    "rugby": [
        "urba",
        "top 12",
        "los pumas",
        "super rugby",
        "rugby championship",
        "world rugby",
    ],
    "hockey": [
        "leonas",
        "leones",
        "pro league",
        "fih",
        "metropolitano",
    ],
    "voley": [
        "aclav",
        "liga argentina",
        "selección argentina",
        "seleccion argentina",
        "feva",
    ],
    "handball": [
        "selección argentina",
        "seleccion argentina",
        "panamericano",
        "mundial",
    ],
    "futsal": [
        "afa",
        "selección argentina",
        "seleccion argentina",
        "liga futsal",
    ],
    "boxeo": [
        "title",
        "titulo",
        "campeonato",
    ],
    "golf": [
        "pga",
        "european tour",
    ],
}

GENERIC_COMPETITION_VALUES = {
    "",
    "fútbol",
    "futbol",
    "football",
    "soccer",
    "tenis",
    "tennis",
    "básquet",
    "basquet",
    "basketball",
    "rugby",
    "hockey",
    "vóley",
    "voley",
    "volleyball",
    "handball",
    "futsal",
    "golf",
    "boxeo",
    "boxing",
    "motorsport",
    "motogp",
    "polo",
    "esports",
    "competencia",
}

SESSION_TOKENS = {
    "practice",
    "práctica",
    "fp1",
    "fp2",
    "fp3",
    "training",
    "entrenamiento",
    "session",
    "qualy",
    "clasificacion",
    "clasificación",
    "sprint",
}

LOW_EDITORIAL_TOKENS = {
    "ii",
    "reserva",
    "filial",
    "amistoso",
    "friendly",
    "academy",
    "u19",
    "u18",
}

HIGH_STAGE_TOKENS = {
    "final",
    "semifinal",
    "semis",
    "cuartos",
    "quarter-final",
    "quarterfinal",
    "playoff",
    "play-offs",
    "mata-mata",
    "knockout",
}


def _to_dict(m: Match | dict[str, Any]) -> dict[str, Any]:
    if isinstance(m, Match):
        d = m.model_dump()
    else:
        d = dict(m)

    if d.get("tv") is None and d.get("broadcast"):
        d["tv"] = d.get("broadcast")

    return d


def _norm_text(v: Any) -> str:
    return str(v or "").strip().lower()


def _combined_text(match: dict[str, Any]) -> str:
    return " ".join(
        [
            _norm_text(match.get("competition")),
            _norm_text(match.get("home_team")),
            _norm_text(match.get("away_team")),
            _norm_text(match.get("argentina_team")),
            _norm_text(match.get("category")),
            _norm_text(match.get("sport")),
        ]
    )


def _contains_any(text: str, tokens: set[str] | list[str] | tuple[str, ...]) -> bool:
    return any(token in text for token in tokens)


def _parse_start_time(value: Any) -> str:
    text = str(value or "").strip()
    return text if text else "99:99"


def _status_order(match: dict[str, Any]) -> int:
    status = _norm_text(match.get("status"))
    return {"live": 0, "upcoming": 1, "finished": 2}.get(status, 9)


def _is_argentina_selection(match: dict[str, Any]) -> bool:
    hay = _combined_text(match)
    return (
        _norm_text(match.get("argentina_relevance")) == "seleccion"
        or "seleccion argentina" in hay
        or "selección argentina" in hay
        or "argentina u17" in hay
        or "argentina u20" in hay
        or "argentina u23" in hay
        or (
            "argentina" in hay
            and (
                "sub 17" in hay
                or "sub-17" in hay
                or "sub 20" in hay
                or "sub-20" in hay
                or "sub 23" in hay
                or "sub-23" in hay
                or "u17" in hay
                or "u20" in hay
                or "u23" in hay
            )
        )
    )


def _is_motorsport(match: dict[str, Any]) -> bool:
    return _norm_text(match.get("sport")) in {"motorsport", "motogp", "dakar"}


def _is_session_event(match: dict[str, Any]) -> bool:
    hay = _combined_text(match)
    return _contains_any(hay, SESSION_TOKENS)


def _is_generic_competition(match: dict[str, Any]) -> bool:
    comp = _norm_text(match.get("competition"))
    return comp in GENERIC_COMPETITION_VALUES


def _is_conmebol(match: dict[str, Any]) -> bool:
    comp = _norm_text(match.get("competition"))
    return _contains_any(comp, CONMEBOL_COMPETITIONS)


def _is_top_exterior(match: dict[str, Any]) -> bool:
    comp = _norm_text(match.get("competition"))
    return _contains_any(comp, TOP_EXTERIOR_COMPETITIONS)


def _is_top_local_football(match: dict[str, Any]) -> bool:
    comp = _norm_text(match.get("competition"))
    return _contains_any(comp, TOP_FOOTBALL_COMPETITIONS)


def _is_second_tier_local_football(match: dict[str, Any]) -> bool:
    comp = _norm_text(match.get("competition"))
    return _contains_any(comp, SECOND_TIER_FOOTBALL_COMPETITIONS)


def _is_local_cup(match: dict[str, Any]) -> bool:
    comp = _norm_text(match.get("competition"))
    return _contains_any(comp, CUP_FOOTBALL_COMPETITIONS)


def _club_weight(text: str) -> int:
    if _contains_any(text, BIG_ARG_CLUBS):
        return 240
    if _contains_any(text, MID_ARG_CLUBS):
        return 120
    return 0


def _has_high_stage(match: dict[str, Any]) -> bool:
    hay = _combined_text(match)
    return _contains_any(hay, HIGH_STAGE_TOKENS)


def _is_local_league(match: dict[str, Any]) -> bool:
    if _norm_text(match.get("argentina_relevance")) == "club_arg":
        return True

    return (
        _is_top_local_football(match)
        or _is_second_tier_local_football(match)
        or _is_local_cup(match)
    )


def _other_sport_bonus(match: dict[str, Any]) -> int:
    sport = _norm_text(match.get("sport"))
    hay = _combined_text(match)

    if sport in OTHER_SPORT_PREMIUM_HINTS:
        if any(token in hay for token in OTHER_SPORT_PREMIUM_HINTS[sport]):
            return 180

    # selecciones de otros deportes
    if _is_argentina_selection(match):
        return 500

    return 0


def _section_for(match: dict[str, Any]) -> str:
    if _is_argentina_selection(match):
        return "selecciones"
    if _is_motorsport(match):
        return "motorsport"
    if _is_local_league(match) or _is_conmebol(match):
        return "ligas_locales"
    return "exterior"


# ─────────────────────────────────────────────────────────────────────────────
# Ranking editorial fino
# ─────────────────────────────────────────────────────────────────────────────

def _editorial_score(match: dict[str, Any]) -> int:
    """
    Más alto = más importante.
    Escala deliberadamente amplia para poder afinar.
    """
    score = 0
    hay = _combined_text(match)
    status = _norm_text(match.get("status"))
    relevance = _norm_text(match.get("argentina_relevance"))
    sport = _norm_text(match.get("sport"))

    # Base por relevancia argentina
    if relevance == "seleccion":
        score += 2200
    elif relevance == "club_arg":
        score += 1100
    elif relevance == "jugador_arg":
        score += 650

    # Deporte base
    if sport == "futbol":
        score += 520
    elif sport == "basquet":
        score += 220
    elif sport == "tenis":
        score += 210
    elif sport == "rugby":
        score += 180
    elif sport == "hockey":
        score += 180
    elif sport == "voley":
        score += 160
    elif sport == "handball":
        score += 140
    elif sport == "futsal":
        score += 140
    elif _is_motorsport(match):
        score += 40
    else:
        score += 80

    # Selección
    if _is_argentina_selection(match):
        score += 2600

    # Fútbol local / copas
    if _is_top_local_football(match):
        score += 1700
    elif _is_local_cup(match):
        score += 1400
    elif _is_second_tier_local_football(match):
        score += 950

    if _is_conmebol(match):
        score += 1300

    # Exterior top
    if _is_top_exterior(match):
        score += 420

    # Otros deportes premium
    score += _other_sport_bonus(match)

    # Clubes
    score += _club_weight(hay)

    # Instancia decisiva
    if _has_high_stage(match):
        score += 280

    # Estado
    if status == "live":
        score += 520
    elif status == "upcoming":
        score += 180
    elif status == "finished":
        score += 40

    # Tener argentino explícito suma
    if _norm_text(match.get("argentina_team")):
        score += 80

    # Tener hora suma un poco
    if _parse_start_time(match.get("start_time")) != "99:99":
        score += 
