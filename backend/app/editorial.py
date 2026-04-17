"""
editorial.py — Ranking editorial reusable para El Tablón Albiceleste.

Objetivos:
- centralizar prioridad editorial para /hoy, /live, /calendario, etc.
- ser extensible a todos los deportes
- evitar heurísticas dispersas dentro de api_hoy.py
"""

from __future__ import annotations

from typing import Any


BIG_ARG_CLUBS = {
    "boca juniors",
    "river plate",
    "racing club",
    "independiente",
    "san lorenzo",
    "newell's old boys",
    "newells old boys",
    "rosario central",
    "velez sarsfield",
    "estudiantes de la plata",
    "huracan",
    "lanus",
    "talleres",
}

MID_ARG_CLUBS = {
    "union de santa fe",
    "belgrano",
    "instituto",
    "platense",
    "banfield",
    "argentinos juniors",
    "defensa y justicia",
    "godoy cruz",
    "tigre",
    "sarmiento",
    "central cordoba",
    "barracas central",
    "aldosivi",
    "quilmes",
    "chacarita juniors",
    "ferro carril oeste",
    "all boys",
    "nueva chicago",
    "patronato",
    "temperley",
    "almirante brown",
    "excursionistas",
    "arsenal de sarandi",
    "deportivo riestra",
    "gimnasia y esgrima la plata",
    "colon de santa fe",
    "atletico tucuman",
    "san martin de tucuman",
    "san martin de san juan",
    "independiente rivadavia",
    "comunicaciones",
}

LOCAL_TOP_COMPETITIONS = {
    "liga profesional",
    "liga profesional de futbol",
    "liga profesional de fútbol",
    "torneo betano",
    "copa argentina",
    "primera nacional",
    "supercopa argentina",
    "trofeo de campeones",
}

LOCAL_MID_COMPETITIONS = {
    "primera b",
    "b metro",
    "primera c",
    "primera d",
    "federal a",
    "federal b",
    "regional amateur",
    "reserva",
    "femenina",
}

CONMEBOL_COMPETITIONS = {
    "libertadores",
    "sudamericana",
    "recopa",
    "conmebol",
}

EXTERIOR_TOP_COMPETITIONS = {
    "premier league",
    "la liga",
    "serie a",
    "bundesliga",
    "ligue 1",
    "champions league",
    "europa league",
    "conference league",
}

MOTORSPORT_SESSION_TOKENS = {
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

GENERIC_COMPETITION_VALUES = {
    "",
    "futbol",
    "fútbol",
    "football",
    "soccer",
    "tenis",
    "tennis",
    "basquet",
    "básquet",
    "basketball",
    "rugby",
    "hockey",
    "voley",
    "vóley",
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
}


def norm_text(v: Any) -> str:
    return str(v or "").strip().lower()


def combined_text(match: dict[str, Any]) -> str:
    return " ".join(
        [
            norm_text(match.get("competition")),
            norm_text(match.get("home_team")),
            norm_text(match.get("away_team")),
            norm_text(match.get("argentina_team")),
            norm_text(match.get("category")),
            norm_text(match.get("sport")),
        ]
    )


def contains_any(text: str, tokens: set[str]) -> bool:
    return any(token in text for token in tokens)


def status_order(match: dict[str, Any]) -> int:
    status = norm_text(match.get("status"))
    return {"live": 0, "upcoming": 1, "finished": 2}.get(status, 9)


def parse_start_time(value: Any) -> str:
    text = str(value or "").strip()
    return text if text else "99:99"


def has_valid_start_time(match: dict[str, Any]) -> bool:
    start = norm_text(match.get("start_time"))
    return bool(start and start not in {"null", "none", "a confirmar", "tbd"})


def is_argentina_selection(match: dict[str, Any]) -> bool:
    hay = combined_text(match)
    return (
        norm_text(match.get("argentina_relevance")) == "seleccion"
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


def is_local_league(match: dict[str, Any]) -> bool:
    comp = norm_text(match.get("competition"))
    if norm_text(match.get("argentina_relevance")) == "club_arg":
        return True
    return contains_any(comp, LOCAL_TOP_COMPETITIONS | LOCAL_MID_COMPETITIONS)


def is_local_top_competition(match: dict[str, Any]) -> bool:
    return contains_any(norm_text(match.get("competition")), LOCAL_TOP_COMPETITIONS)


def is_local_mid_competition(match: dict[str, Any]) -> bool:
    return contains_any(norm_text(match.get("competition")), LOCAL_MID_COMPETITIONS)


def is_conmebol(match: dict[str, Any]) -> bool:
    return contains_any(norm_text(match.get("competition")), CONMEBOL_COMPETITIONS)


def is_top_exterior(match: dict[str, Any]) -> bool:
    return contains_any(norm_text(match.get("competition")), EXTERIOR_TOP_COMPETITIONS)


def is_motorsport(match: dict[str, Any]) -> bool:
    return norm_text(match.get("sport")) in {"motorsport", "motogp", "dakar"}


def is_session_event(match: dict[str, Any]) -> bool:
    return contains_any(combined_text(match), MOTORSPORT_SESSION_TOKENS)


def is_generic_competition(match: dict[str, Any]) -> bool:
    return norm_text(match.get("competition")) in GENERIC_COMPETITION_VALUES


def is_exterior(match: dict[str, Any]) -> bool:
    return (
        norm_text(match.get("argentina_relevance")) == "jugador_arg"
        and not is_motorsport(match)
    )


def sport_weight(match: dict[str, Any]) -> int:
    sport = norm_text(match.get("sport"))

    if sport == "futbol":
        return 240
    if sport == "basquet":
        return 140
    if sport == "tenis":
        return 120
    if sport == "rugby":
        return 110
    if sport == "hockey":
        return 110
    if sport == "voley":
        return 95
    if sport == "handball":
        return 90
    if sport == "futsal":
        return 85
    if sport == "boxeo":
        return 75
    if sport == "golf":
        return 60
    if is_motorsport(match):
        return 40

    return 50


def club_name_weight(name: Any) -> int:
    n = norm_text(name)

    if any(token in n for token in BIG_ARG_CLUBS):
        return 230

    if any(token in n for token in MID_ARG_CLUBS):
        return 120

    return 0


def teams_weight(match: dict[str, Any]) -> int:
    return club_name_weight(match.get("home_team")) + club_name_weight(match.get("away_team"))


def competition_weight(match: dict[str, Any]) -> int:
    if is_local_top_competition(match):
        return 420

    if is_local_mid_competition(match):
        return 220

    if is_conmebol(match):
        return 360

    if is_top_exterior(match):
        return 120

    return 0


def status_weight(match: dict[str, Any]) -> int:
    status = norm_text(match.get("status"))

    if status == "live":
        return 420
    if status == "upcoming":
        return 180
    if status == "finished":
        return 40

    return 0


def relevance_weight(match: dict[str, Any]) -> int:
    relevance = norm_text(match.get("argentina_relevance"))

    if relevance == "seleccion":
        return 1500
    if relevance == "club_arg":
        return 820
    if relevance == "jugador_arg":
        return 420

    return 0


def selection_weight(match: dict[str, Any]) -> int:
    if not is_argentina_selection(match):
        return 0

    hay = combined_text(match)

    if "mayor" in hay:
        return 900
    if "u23" in hay or "sub 23" in hay or "sub-23" in hay:
        return 700
    if "u20" in hay or "sub 20" in hay or "sub-20" in hay:
        return 650
    if "u17" in hay or "sub 17" in hay or "sub-17" in hay:
        return 620

    return 800


def quality_penalty(match: dict[str, Any]) -> int:
    hay = combined_text(match)
    penalty = 0

    if is_motorsport(match):
        penalty += 140

    if is_session_event(match):
        penalty += 320

    if " ii" in f" {hay}" or " reserva" in f" {hay}" or " filial" in hay:
        penalty += 220

    if "amistoso" in hay or "friendly" in hay:
        penalty += 170

    if is_generic_competition(match):
        penalty += 220

    if not has_valid_start_time(match):
        penalty += 70

    return penalty


def editorial_score(match: dict[str, Any]) -> int:
    score = 0

    score += relevance_weight(match)
    score += selection_weight(match)
    score += sport_weight(match)
    score += competition_weight(match)
    score += teams_weight(match)
    score += status_weight(match)

    if norm_text(match.get("argentina_team")):
        score += 50

    if is_exterior(match) and is_top_exterior(match):
        score += 80

    score -= quality_penalty(match)

    return score


def section_for(match: dict[str, Any]) -> str:
    if is_argentina_selection(match):
        return "selecciones"
    if is_local_league(match) or is_conmebol(match):
        return "ligas_locales"
    if is_motorsport(match):
        return "motorsport"
    return "exterior"


def sort_key(match: dict[str, Any]) -> tuple:
    return (
        status_order(match),
        -editorial_score(match),
        parse_start_time(match.get("start_time")),
        norm_text(match.get("competition")),
        norm_text(match.get("home_team")),
    )


def hero_sort_key(match: dict[str, Any]) -> tuple:
    return (
        -editorial_score(match),
        status_order(match),
        parse_start_time(match.get("start_time")),
        norm_text(match.get("competition")),
        norm_text(match.get("home_team")),
    )


def pick_hero(matches: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not matches:
        return None
    return sorted(matches, key=hero_sort_key)[0]
