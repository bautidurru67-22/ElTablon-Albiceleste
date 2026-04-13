"""
Detector de relevancia argentina.
Usa normalize_str() en todas las comparaciones para manejar tildes/acentos.
"""
from __future__ import annotations
import unicodedata
import logging
import re
from scraping.models import ArgRelevance

logger = logging.getLogger(__name__)


def normalize_str(s: str) -> str:
    """Minúsculas + sin acentos. 'Atlético' → 'atletico'."""
    return (
        unicodedata.normalize("NFKD", s.lower().strip())
        .encode("ascii", "ignore")
        .decode("ascii")
    )


# ---------------------------------------------------------------------------
# SELECCIONES — exactas O substring en nombre normalizado
# ---------------------------------------------------------------------------
_NATIONAL: set[str] = {
    "argentina", "seleccion argentina", "argentina u20", "argentina u23",
    "argentina u17", "argentina u15", "argentina women", "argentina female",
    "argentina men", "los pumas", "argentina rugby", "argentina xv",
    "argentina 7s", "pumitas", "las leonas", "los leones", "argentina hockey",
    "las panteras", "la albiceleste", "argentina basket", "argentina basketball",
    "arg",   # abreviatura internacional (FIH, FIBA, etc.)
    "arg women", "arg men", "arg u20", "arg u23",
}

# ---------------------------------------------------------------------------
# CLUBES — clave = nombre SIN acentos, minúsculas
# ---------------------------------------------------------------------------
_CLUBS: dict[str, str] = {
    # ── Fútbol ─────────────────────────────────────────────────────────────
    "river plate": "river", "boca juniors": "boca",
    "racing club": "racing", "racing": "racing",
    "independiente": "independiente",
    "san lorenzo": "sanlorenzo",
    "huracan": "huracan",
    "estudiantes": "estudiantes", "estudiantes lp": "estudiantes",
    "lanus": "lanus",
    "velez sarsfield": "velez", "velez": "velez",
    "talleres": "talleres",
    "atletico tucuman": "atleticotucuman",
    "athletico tucuman": "atleticotucuman",
    "platense": "platense",
    "tigre": "tigre",
    "ferro": "ferro",
    "quilmes": "quilmes",
    "belgrano": "belgrano",
    "godoy cruz": "godoycruz",
    "central cordoba": "centralcordoba",
    "rosario central": "rosariocentral",
    "newells old boys": "newells", "newells": "newells",
    "san martin": "sanmartin",
    "instituto": "instituto",
    "colon": "colon",
    "union": "union",
    "defensa y justicia": "defensa",
    "argentinos juniors": "argentinos",
    "banfield": "banfield",
    "barracas central": "barracas",
    "sarmiento": "sarmiento",
    "gimnasia la plata": "gimnasia", "gimnasia y esgrima": "gimnasia",
    "aldosivi": "aldosivi",
    "patronato": "patronato",
    "chacarita": "chacarita",
    "all boys": "allboys",
    "deportivo riestra": "riestra",
    "arsenal": "arsenal",
    "temperley": "temperley",
    # ── Básquet LNB ─────────────────────────────────────────────────────────
    "obras basket": "obras", "obras sanitarias": "obras",
    "quimsa": "quimsa",
    "regatas corrientes": "regatas", "regatas": "regatas",
    "penarol mar del plata": "penarol",
    "san lorenzo basquet": "slbasquet",
    "olimpico de la banda": "olimpico", "olimpico": "olimpico",
    "weber bahia": "weberbahia",
    "libertad sunchales": "libertad", "libertad": "libertad",
    "comunicaciones": "comunicaciones",
    "boca juniors basquet": "bocabasquet",
    "river plate basquet": "riverbasquet",
    "la union formosa": "launion",
    "atletico cordoba": "atleticocba",
    # ── Rugby ────────────────────────────────────────────────────────────────
    "casi": "casi", "sic": "sic", "hindu": "hindu",
    "newman": "newman", "pucara": "pucara",
    "belgrano athletic": "belgranoath",
    "jaguares": "jaguares", "jaguares xv": "jaguaresxv",
    # ── Hockey ──────────────────────────────────────────────────────────────
    "club san fernando": "sanfernandohk",
    # ── Vóley ───────────────────────────────────────────────────────────────
    "upcn san juan": "upcn",
    "personal bolivar": "bolivar", "bolivar voley": "bolivar",
    "lomas voley": "lomas",
    # ── Polo ────────────────────────────────────────────────────────────────
    "la dolfina": "ladolfina", "ellerstina": "ellerstina",
}

# ---------------------------------------------------------------------------
# JUGADORES — clave = nombre SIN acentos, minúsculas
# ---------------------------------------------------------------------------
ARG_PLAYERS: dict[str, str] = {
    # Tenis ATP
    "cerundolo": "cerundolo", "francisco cerundolo": "cerundolo",
    "etcheverry": "etcheverry", "tomas etcheverry": "etcheverry",
    "baez": "baez", "sebastian baez": "baez",
    "navone": "navone", "mariano navone": "navone",
    "delbonis": "delbonis", "federico delbonis": "delbonis",
    "zeballos": "zeballos", "horacio zeballos": "zeballos",
    "schwartzman": "schwartzman", "diego schwartzman": "schwartzman",
    "pella": "pella", "mayer": "mayer",
    "maximo gonzalez": "mgonzalez",
    "andreozzi": "andreozzi",
    # Básquet
    "campazzo": "campazzo", "facundo campazzo": "campazzo",
    "bolmaro": "bolmaro", "leandro bolmaro": "bolmaro",
    "laprovittola": "laprovittola", "nicolas laprovittola": "laprovittola",
    "vildoza": "vildoza", "luca vildoza": "vildoza",
    "deck": "deck", "gabriel deck": "deck",
    "brussino": "brussino",
    # Fútbol exterior
    "messi": "messi", "lionel messi": "messi",
    "lautaro martinez": "lautaro",
    "julian alvarez": "jalvarez",
    "enzo fernandez": "enzof",
    "alejandro garnacho": "garnacho",
    "mac allister": "macallister", "alexis mac allister": "macallister",
    "dybala": "dybala", "paulo dybala": "dybala",
    "di maria": "dimaria", "angel di maria": "dimaria",
    "icardi": "icardi", "mauro icardi": "icardi",
    "rodrigo de paul": "depaul",
    "nahuel molina": "molina",
    "lisandro martinez": "lisandrom",
    "cuti romero": "cutiromero", "cristian romero": "cutiromero",
    "german pezzella": "pezzella",
    "nicolas gonzalez": "nicogonzalez",
    "valentin castellanos": "castellanos",
    "thiago almada": "almada",
    # F1 / MotoGP
    "colapinto": "colapinto", "franco colapinto": "colapinto",
    "augusto fernandez": "augfernandez",
    # Rugby
    "nicolas sanchez": "nsanchez",
    "emiliano boffelli": "boffelli",
    "santiago carreras": "scarreras",
    "matias moroni": "moroni",
    # Boxeo
    "brian castano": "castano",
    # Golf
    "emiliano grillo": "grillo",
    "fabian gomez": "fgomez",
    # Hockey
    "gonzalo peillat": "peillat",
}

# Nombres que NO son argentinos aunque suenen parecido
_NON_ARG: set[str] = {"piastri", "arg and"}

# Competencias cuyo nombre implica que es argentina
_ARG_COMPETITIONS: list[str] = [
    "liga profesional argentina",
    "copa argentina",
    "primera division argentina",
    "torneo federal a",
    "liga nacional de basquet",
    "liga nacional basquet",
    "urba top 14",
    "superrugby americas",
    "liga argentina de hockey",
    "liga nacional de voley",
    "primera division argentina futsal",
]

# También exponer ARG_CLUBS para compatibilidad con adapters
ARG_CLUBS: dict[str, str] = _CLUBS


def detect_argentina_relevance(
    home: str,
    away: str,
    competition: str = "",
    sport: str = "",
) -> tuple[ArgRelevance, str | None]:
    """
    Retorna (relevance, team_name).
    Orden: seleccion > club_arg > jugador_arg > competencia_arg > none
    """
    hn = normalize_str(home)
    an = normalize_str(away)
    cn = normalize_str(competition)

    def _contains(name_norm: str, hay_norm: str) -> bool:
        # Tokens cortos (ej: "arg") deben matchear palabra completa
        if len(name_norm) <= 3:
            return re.search(rf"\b{re.escape(name_norm)}\b", hay_norm) is not None
        return name_norm in hay_norm

    # 1. Selección nacional
    for name in _NATIONAL:
        nn = normalize_str(name)
        if nn and _contains(nn, hn):
            return "seleccion", home
        if nn and _contains(nn, an):
            return "seleccion", away

    # 2. Club argentino
    for club_n in _CLUBS:
        if club_n in hn:
            return "club_arg", home
        if club_n in an:
            return "club_arg", away

    # 3. Jugador argentino
    for player_n, pid in ARG_PLAYERS.items():
        pn = normalize_str(player_n)
        if pn in _NON_ARG:
            continue
        if pn and pn in hn:
            return "jugador_arg", home
        if pn and pn in an:
            return "jugador_arg", away

    # 4. Competencia argentina (club_arg en home por defecto)
    for ck in _ARG_COMPETITIONS:
        if ck in cn:
            return "club_arg", home

    return "none", None


def is_argentina_club(name: str) -> bool:
    n = normalize_str(name)
    return any(k in n for k in _CLUBS)


def get_club_id(name: str) -> str | None:
    n = normalize_str(name)
    for k, v in _CLUBS.items():
        if k in n:
            return v
    return None


def get_player_id(name: str) -> str | None:
    n = normalize_str(name)
    for k, v in ARG_PLAYERS.items():
        if normalize_str(k) in n:
            return v
    return None
