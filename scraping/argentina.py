"""
Detector de relevancia argentina.
Centraliza toda la lógica de identificación: selecciones, clubes y jugadores.
"""
from __future__ import annotations
from scraping.models import ArgRelevance

# ---------------------------------------------------------------------------
# SELECCIONES NACIONALES
# ---------------------------------------------------------------------------
ARGENTINA_NATIONAL_TEAMS: set[str] = {
    "argentina",
    "selección argentina",
    "argentina u20",
    "argentina u23",
    "los pumas",
    "las leonas",
    "los leones",
    "las panteras",
    "la albiceleste",
    "argentina 7s",
}

# ---------------------------------------------------------------------------
# CLUBES ARGENTINOS  (nombre normalizado → id interno)
# ---------------------------------------------------------------------------
ARG_CLUBS: dict[str, str] = {
    # Fútbol — Primera División
    "river plate": "arg-river",
    "boca juniors": "arg-boca",
    "racing club": "arg-racing",
    "independiente": "arg-independiente",
    "san lorenzo": "arg-sanlorenzo",
    "huracán": "arg-huracan",
    "huracan": "arg-huracan",
    "estudiantes": "arg-estudiantes",
    "lanús": "arg-lanus",
    "lanus": "arg-lanus",
    "vélez sársfield": "arg-velez",
    "velez": "arg-velez",
    "talleres": "arg-talleres",
    "athletico tucumán": "arg-tucuman",
    "atletico tucuman": "arg-tucuman",
    "platense": "arg-platense",
    "tigre": "arg-tigre",
    "ferro": "arg-ferro",
    "quilmes": "arg-quilmes",
    "belgrano": "arg-belgrano",
    "godoy cruz": "arg-godoycruz",
    "central córdoba": "arg-centralcordoba",
    "central cordoba": "arg-centralcordoba",
    "rosario central": "arg-rosariocentral",
    "newell's old boys": "arg-newells",
    "newells": "arg-newells",
    "san martín de formosa": "arg-sanmartinfsa",
    "san martin de formosa": "arg-sanmartinfsa",
    "instituto": "arg-instituto",
    # Básquet
    "obras basket": "arg-obras",
    "quimsa": "arg-quimsa",
    "regatas": "arg-regatas",
    "peñarol mar del plata": "arg-penarol",
    "penarol": "arg-penarol",
    "san lorenzo basquet": "arg-sanlorenzo-bsq",
    "olimpico": "arg-olimpico",
    "olímpico": "arg-olimpico",
    "weber bahia": "arg-weberbahia",
    "libertad": "arg-libertad",
    "comunicaciones": "arg-comunicaciones",
    # Rugby URBA + SuperRugby
    "casi": "arg-casi",
    "sic": "arg-sic",
    "hindú": "arg-hindu",
    "hindu": "arg-hindu",
    "newman": "arg-newman",
    "pucará": "arg-pucara",
    "pucara": "arg-pucara",
    "belgrano athletic": "arg-belgrano-ath",
    "bac": "arg-bac",
    "jaguares": "arg-jaguares",
    "jaguares xv": "arg-jaguares-xv",
    # Hockey (field hockey)
    "club san fernando": "arg-sanfernando-hk",
    "universitario la plata": "arg-unilp-hk",
    # Vóley
    "upcn san juan": "arg-upcn",
    "personal bolivar": "arg-bolivar",
    "bolivar voley": "arg-bolivar",
    "lomas voley": "arg-lomas",
    # Polo
    "la dolfina": "arg-ladolfina",
    "ellerstina": "arg-ellerstina",
}

# ---------------------------------------------------------------------------
# JUGADORES ARGENTINOS  (nombre lowercase → id interno)
# ---------------------------------------------------------------------------
ARG_PLAYERS: dict[str, str] = {
    # Tenis ATP
    "cerúndolo": "arg-cerundolo",
    "cerundolo": "arg-cerundolo",
    "francisco cerúndolo": "arg-cerundolo",
    "francisco cerundolo": "arg-cerundolo",
    "etcheverry": "arg-etcheverry",
    "tomás etcheverry": "arg-etcheverry",
    "tomas etcheverry": "arg-etcheverry",
    "báez": "arg-baez",
    "baez": "arg-baez",
    "sebastián báez": "arg-baez",
    "sebastian baez": "arg-baez",
    "navone": "arg-navone",
    "mariano navone": "arg-navone",
    "delbonis": "arg-delbonis",
    "federico delbonis": "arg-delbonis",
    "zeballos": "arg-zeballos",
    "horacio zeballos": "arg-zeballos",
    "granollers": "arg-granollers",
    "máximo gonzález": "arg-mgonzalez",
    "maximo gonzalez": "arg-mgonzalez",
    "schwartzman": "arg-schwartzman",
    "diego schwartzman": "arg-schwartzman",
    "pella": "arg-pella",
    "mayer": "arg-mayer",
    # Básquet NBA
    "campazzo": "arg-campazzo",
    "facundo campazzo": "arg-campazzo",
    "bolmaro": "arg-bolmaro",
    "leandro bolmaro": "arg-bolmaro",
    "laprovíttola": "arg-laprovittola",
    "laprovittola": "arg-laprovittola",
    "nicolás laprovíttola": "arg-laprovittola",
    # Fútbol exterior
    "lautaro martínez": "arg-lautaro",
    "lautaro martinez": "arg-lautaro",
    "julián álvarez": "arg-jalvarez",
    "julian alvarez": "arg-jalvarez",
    "rodrigo de paul": "arg-depaul",
    "enzo fernández": "arg-enzof",
    "enzo fernandez": "arg-enzof",
    "alejandro garnacho": "arg-garnacho",
    "mac allister": "arg-macallister",
    "alexis mac allister": "arg-macallister",
    "icardi": "arg-icardi",
    "mauro icardi": "arg-icardi",
    # Automovilismo F1 / F2
    "colapinto": "arg-colapinto",
    "franco colapinto": "arg-colapinto",
    "piastri": None,  # australiano — evitar falso positivo
    # MotoGP
    "augusto fernandez": "arg-augfernandez",
    "augusto fernández": "arg-augfernandez",
    # Rugby (jugadores individuales — 7s y stats)
    "nicolás sánchez": "arg-nsanchez",
    "nicolas sanchez": "arg-nsanchez",
    "emiliano boffelli": "arg-boffelli",
    "santiago carreras": "arg-scarreras",
    # Boxeo
    "brian castaño": "arg-castano",
    "brian castano": "arg-castano",
    # Golf
    "angel cabrera": "arg-cabrera",
    "emiliano grillo": "arg-grillo",
    "fabian gomez": "arg-fgomez",
    # Hockey
    "gonzalo peillat": "arg-peillat",
    # Atletismo / natación olímpica
    "belén casetta": "arg-casetta",
    "delfina pignatiello": "arg-pignatiello",
}

# Jugadores que no son ARG pero tienen nombres similares (evitar FP)
NON_ARGENTINA_OVERRIDE: set[str] = {"piastri"}


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------

def detect_argentina_relevance(
    home: str,
    away: str,
    competition: str = "",
    sport: str = "",
) -> tuple[ArgRelevance, str | None]:
    """
    Retorna (argentina_relevance, argentina_team_name).
    Orden de prioridad: seleccion > club_arg > jugador_arg > none
    """
    home_n = home.lower().strip()
    away_n = away.lower().strip()
    comp_n = competition.lower().strip()

    # 1. Selección nacional
    for name in ARGENTINA_NATIONAL_TEAMS:
        if name in home_n:
            return "seleccion", home
        if name in away_n:
            return "seleccion", away

    # 2. Club argentino
    for club_name, _club_id in ARG_CLUBS.items():
        if club_name in home_n:
            return "club_arg", home
        if club_name in away_n:
            return "club_arg", away

    # 3. Jugador argentino (relevante para tenis, boxeo, golf, etc.)
    for player_name, player_id in ARG_PLAYERS.items():
        if player_id is None:
            continue  # override — no es ARG
        if player_name in home_n and home_n not in NON_ARGENTINA_OVERRIDE:
            return "jugador_arg", home
        if player_name in away_n and away_n not in NON_ARGENTINA_OVERRIDE:
            return "jugador_arg", away

    return "none", None


def is_argentina_club(name: str) -> bool:
    return name.lower().strip() in ARG_CLUBS


def get_club_id(name: str) -> str | None:
    return ARG_CLUBS.get(name.lower().strip())


def get_player_id(name: str) -> str | None:
    return ARG_PLAYERS.get(name.lower().strip())
