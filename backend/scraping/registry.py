"""
Registry central de adapters + agregador Argentina-first para El Tablón Albiceleste.

Objetivos:
- Safe imports: un adapter roto no rompe todo
- Cache por deporte y por fecha
- Timeout por deporte para evitar 504
- Resumen diario unificado para /api/hoy, /api/live, /api/resultados, /api/calendario
- Secciones editoriales:
    1) selecciones
    2) ligas_locales
    3) exterior
    4) motorsport
"""

from __future__ import annotations

import asyncio
import importlib
import logging
import re
from copy import deepcopy
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from scraping.base_scraper import BaseScraper

logger = logging.getLogger(__name__)

ART_TZ = ZoneInfo("America/Argentina/Buenos_Aires")
SCRAPER_TIMEOUT_SECONDS = 8

LOAD_ERRORS: dict[str, str] = {}
_SUMMARY_CACHE: dict[str, dict[str, Any]] = {}
_SPORT_CACHE: dict[tuple[str, str], list[dict[str, Any]]] = {}


# -------------------------------------------------------------------
# Carga segura de adapters
# -------------------------------------------------------------------

def _load(module: str, cls: str):
    try:
        return getattr(importlib.import_module(module), cls)
    except Exception as e:
        msg = f"{type(e).__name__}: {e}"
        logger.error(f"[registry] no se pudo cargar {cls} desde {module}: {msg}")
        LOAD_ERRORS[f"{module}.{cls}"] = msg
        return None


_MAP = {
    "futbol": ("scraping.adapters.football", "FootballAdapter"),
    "tenis": ("scraping.adapters.tennis", "TennisAdapter"),
    "basquet": ("scraping.adapters.basketball", "BasketballAdapter"),
    "rugby": ("scraping.adapters.rugby", "RugbyAdapter"),
    "hockey": ("scraping.adapters.hockey", "HockeyAdapter"),
    "voley": ("scraping.adapters.volleyball", "VolleyballAdapter"),
    "handball": ("scraping.adapters.handball", "HandballAdapter"),
    "futsal": ("scraping.adapters.futsal", "FutsalAdapter"),
    "motorsport": ("scraping.adapters.motorsport", "MotorsportAdapter"),
    "motogp": ("scraping.adapters.motogp", "MotoGPAdapter"),
    "boxeo": ("scraping.adapters.boxing", "BoxingAdapter"),
    "golf": ("scraping.adapters.golf", "GolfAdapter"),
    "esports": ("scraping.adapters.esports", "EsportsAdapter"),
    "polo": ("scraping.adapters.polo", "PoloAdapter"),
    "dakar": ("scraping.adapters.dakar", "DakarAdapter"),
    "olimpicos": ("scraping.adapters.olympics", "OlympicsAdapter"),
}

ADAPTER_REGISTRY: dict[str, type[BaseScraper]] = {}

for sport, (mod, cls_name) in _MAP.items():
    cls = _load(mod, cls_name)
    if cls is not None:
        ADAPTER_REGISTRY[sport] = cls

logger.info(f"[registry] activos: {list(ADAPTER_REGISTRY.keys())}")


# -------------------------------------------------------------------
# Reglas editoriales
# -------------------------------------------------------------------

ARGENTINA_SELECTION_PATTERNS = [
    r"\bargentina\b",
    r"\bselecci[oó]n argentina\b",
    r"\balbiceleste\b",
    r"\bsub[- ]?17\b",
    r"\bsub[- ]?20\b",
    r"\bsub[- ]?23\b",
    r"\bu17\b",
    r"\bu20\b",
    r"\bu23\b",
    r"\bjuvenil(?:es)?\b",
    r"\bfemenina\b",
    r"\bfemenino\b",
    r"\bwomen\b",
]

ARGENTINE_CLUBS = {
    "river plate",
    "club atletico river plate",
    "boca juniors",
    "club atletico boca juniors",
    "racing",
    "racing club",
    "racing club avellaneda",
    "independiente",
    "club atletico independiente",
    "san lorenzo",
    "san lorenzo de almagro",
    "club atletico san lorenzo",
    "estudiantes",
    "estudiantes de la plata",
    "club estudiantes de la plata",
    "gimnasia",
    "gimnasia y esgrima la plata",
    "lanus",
    "club atletico lanus",
    "banfield",
    "club atletico banfield",
    "velez",
    "velez sarsfield",
    "club atletico velez sarsfield",
    "argentinos juniors",
    "aa argentinos juniors",
    "talleres",
    "talleres de cordoba",
    "ca talleres",
    "belgrano",
    "club atletico belgrano",
    "belgrano de cordoba",
    "newells",
    "newells old boys",
    "newell's old boys",
    "rosario central",
    "club atletico rosario central",
    "defensa y justicia",
    "club defensa y justicia",
    "huracan",
    "club atletico huracan",
    "platense",
    "club atletico platense",
    "sarmiento",
    "sarmiento de junin",
    "tigre",
    "club atletico tigre",
    "barracas central",
    "club atletico barracas central",
    "instituto",
    "instituto acc",
    "instituto de cordoba",
    "union de santa fe",
    "union santa fe",
    "club atletico union de santa fe",
    "arsenal de sarandi",
    "arsenal sarandi",
    "colon",
    "colon de santa fe",
    "club atletico colon",
    "atletico tucuman",
    "club atletico tucuman",
    "aldosivi",
    "club atletico aldosivi",
    "central cordoba",
    "central cordoba sde",
    "central cordoba santiago del estero",
    "independiente rivadavia",
    "deportivo riestra",
    "riestra",
    "godoy cruz",
    "godoy cruz antonio tomba",
    "ferro",
    "ferro carril oeste",
    "quilmes",
    "quilmes atletico club",
    "san martin de tucuman",
    "san martin tucuman",
    "san martin de san juan",
    "all boys",
    "almagro",
    "almirante brown",
    "agropecuario",
    "atlanta",
    "brown de adrogue",
    "chacarita",
    "chacarita juniors",
    "chaco for ever",
    "defensores de belgrano",
    "deportivo madryn",
    "deportivo maipu",
    "deportivo moron",
    "estudiantes de rio cuarto",
    "gimnasia de mendoza",
    "gimnasia y esgrima de mendoza",
    "gimnasia de jujuy",
    "los andes",
    "mitre",
    "nueva chicago",
    "patronato",
    "san miguel",
    "temperley",
    "tristan suarez",
}

LOCAL_COMPETITION_PATTERNS = [
    "liga profesional",
    "liga profesional argentina",
    "torneo betano",
    "primera division",
    "primera división",
    "primera nacional",
    "nacional b",
    "b nacional",
    "primera b",
    "primera b metropolitana",
    "b metro",
    "primera c",
    "primera d",
    "promocional amateur",
    "federal a",
    "federal b",
    "regional amateur",
    "torneo federal",
    "copa argentina",
    "copa de la liga",
    "supercopa argentina",
    "supercopa internacional",
    "trofeo de campeones",
    "reserva",
    "torneo de reserva",
    "primera femenina",
    "primera division femenina",
    "primera división femenina",
    "futbol femenino",
    "fútbol femenino",
    "juveniles",
    "juveniles afa",
]

INTERNATIONAL_COMPETITION_PATTERNS = [
    "libertadores",
    "sudamericana",
    "recopa sudamericana",
    "conmebol libertadores",
    "conmebol sudamericana",
    "conmebol recopa",
]

MOTORSPORT_ARG_PATTERNS = [
    "colapinto",
    "franco colapinto",
    "argentina",
    "argentino",
    "turismo carretera",
    "tc ",
    "top race",
    "turismo nacional",
    "tn clase",
    "superbike argentino",
]

STATUS_ALIASES = {
    "live": "live",
    "inplay": "live",
    "in_play": "live",
    "playing": "live",
    "ongoing": "live",
    "1h": "live",
    "2h": "live",
    "ht": "live",
    "upcoming": "upcoming",
    "scheduled": "upcoming",
    "not_started": "upcoming",
    "ns": "upcoming",
    "time_to_be_defined": "upcoming",
    "tbd": "upcoming",
    "postponed": "upcoming",
    "finished": "finished",
    "final": "finished",
    "ended": "finished",
    "ft": "finished",
}

SECTION_ORDER = {
    "selecciones": 0,
    "ligas_locales": 1,
    "exterior": 2,
    "motorsport": 3,
    "otros": 4,
}

SPORT_ORDER = {
    "futbol": 0,
    "tenis": 1,
    "basquet": 2,
    "rugby": 3,
    "hockey": 4,
    "voley": 5,
    "futsal": 6,
    "handball": 7,
    "motorsport": 8,
    "motogp": 9,
    "boxeo": 10,
    "golf": 11,
    "polo": 12,
    "esports": 13,
    "dakar": 14,
    "olimpicos": 15,
}


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def _now_art() -> datetime:
    return datetime.now(ART_TZ)


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower()
    text = (
        text.replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ü", "u")
        .replace("'", "")
        .replace(".", " ")
        .replace(",", " ")
        .replace("-", " ")
        .replace("_", " ")
        .replace("/", " ")
    )
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _safe_str(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _first_non_empty(d: dict[str, Any], keys: list[str], default: Any = None) -> Any:
    for key in keys:
        value = d.get(key)
        if value not in (None, "", [], {}):
            return value
    return default


def _normalize_status(value: Any) -> str:
    raw = _normalize_text(value)
    return STATUS_ALIASES.get(raw, raw or "upcoming")


def _infer_sport(match: dict[str, Any], fallback_sport: str) -> str:
    candidates = [
        match.get("sport"),
        match.get("deporte"),
        match.get("sport_key"),
        fallback_sport,
    ]
    for candidate in candidates:
        text = _normalize_text(candidate)
        if text:
            return text
    return fallback_sport


def _extract_match_datetime(match: dict[str, Any]) -> str | None:
    return _first_non_empty(
        match,
        ["start_time", "datetime", "date_time", "kickoff", "starts_at", "scheduled_at", "utc_date", "date"],
    )


def _normalize_match(raw_match: Any, fallback_sport: str) -> dict[str, Any]:
    if isinstance(raw_match, dict):
        data = dict(raw_match)
    elif hasattr(raw_match, "to_backend_dict"):
        data = raw_match.to_backend_dict()
    elif hasattr(raw_match, "__dict__"):
        data = dict(vars(raw_match))
    else:
        data = {"raw": str(raw_match)}

    home = _first_non_empty(data, ["home_team", "home", "team1", "local", "player1"], "")
    away = _first_non_empty(data, ["away_team", "away", "team2", "visitor", "player2"], "")
    competition = _first_non_empty(data, ["competition", "tournament", "league", "torneo"], "")
    status = _normalize_status(_first_non_empty(data, ["status", "state"], "upcoming"))
    sport = _infer_sport(data, fallback_sport)

    normalized = {
        "id": _safe_str(_first_non_empty(data, ["id", "match_id", "event_id"], "")),
        "sport": sport,
        "competition": _safe_str(competition),
        "home_team": _safe_str(home),
        "away_team": _safe_str(away),
        "home_score": _first_non_empty(data, ["home_score", "score_home", "team1_score"], 0),
        "away_score": _first_non_empty(data, ["away_score", "score_away", "team2_score"], 0),
        "status": status,
        "start_time": _extract_match_datetime(data),
        "tv": _first_non_empty(data, ["tv", "broadcast", "channel"], None),
        "source": _safe_str(_first_non_empty(data, ["source", "provider"], "")),
        "source_priority": _first_non_empty(data, ["source_priority"], 99),
        "round": _safe_str(_first_non_empty(data, ["round", "stage"], "")),
        "category": _safe_str(_first_non_empty(data, ["category", "section"], "")),
        "argentina_reason": _safe_str(_first_non_empty(data, ["argentina_reason"], "")),
        "argentina_entities": _first_non_empty(data, ["argentina_entities"], []) or [],
        "raw": data,
    }

    if not normalized["id"]:
        normalized["id"] = (
            f"{sport}|{normalized['competition']}|{normalized['home_team']}|"
            f"{normalized['away_team']}|{normalized['start_time']}"
        )

    return normalized


def _is_selection_name(name: str) -> bool:
    text = _normalize_text(name)
    if not text:
        return False
    return any(re.search(pattern, text) for pattern in ARGENTINA_SELECTION_PATTERNS)


def _is_exact_argentine_club(name: str) -> bool:
    text = _normalize_text(name)
    return text in ARGENTINE_CLUBS


def _is_local_competition(name: str) -> bool:
    text = _normalize_text(name)
    if not text:
        return False
    return any(pattern in text for pattern in LOCAL_COMPETITION_PATTERNS)


def _is_international_competition(name: str) -> bool:
    text = _normalize_text(name)
    if not text:
        return False
    return any(pattern in text for pattern in INTERNATIONAL_COMPETITION_PATTERNS)


def _is_generic_competition(name: str) -> bool:
    text = _normalize_text(name)
    return text in {"futbol", "football", "soccer", ""}


def _is_motorsport_argentina_related(match: dict[str, Any]) -> bool:
    haystack = " ".join(
        [
            _safe_str(match.get("competition")),
            _safe_str(match.get("home_team")),
            _safe_str(match.get("away_team")),
            _safe_str(match.get("round")),
            _safe_str(match.get("source")),
            _safe_str(match.get("raw")),
        ]
    ).lower()
    return any(pattern in haystack for pattern in MOTORSPORT_ARG_PATTERNS)


def clasificar_partido(match: dict[str, Any]) -> str | None:
    home = _safe_str(match.get("home_team"))
    away = _safe_str(match.get("away_team"))
    comp = _safe_str(match.get("competition"))
    sport = _normalize_text(match.get("sport"))

    if sport not in {"futbol", "football", "soccer"}:
        if sport in {"motorsport", "motogp", "dakar"} and _is_motorsport_argentina_related(match):
            return "motorsport"
        return None

    # Selección
    if _is_selection_name(home) or _is_selection_name(away):
        return "selecciones"

    home_arg = _is_exact_argentine_club(home)
    away_arg = _is_exact_argentine_club(away)

    # Ligas locales: si la competencia es local argentina
    if _is_local_competition(comp):
        # si ambos parecen argentinos, mejor; si no, igual es local por competencia
        return "ligas_locales"

    # Exterior: SOLO si es competencia internacional real y hay club argentino exacto
    if _is_international_competition(comp) and (home_arg or away_arg):
        return "exterior"

    # Competencia genérica: solo conservar si ambos clubes son argentinos -> ligas_locales
    if _is_generic_competition(comp):
        if home_arg and away_arg:
            return "ligas_locales"
        return None

    # Todo lo demás se descarta
    return None


def _status_priority(status: str) -> int:
    if status == "live":
        return 0
    if status == "upcoming":
        return 1
    if status == "finished":
        return 2
    return 9


def _sort_key(match: dict[str, Any]):
    category = _normalize_text(match.get("category"))
    sport = _normalize_text(match.get("sport"))
    return (
        _status_priority(_normalize_text(match.get("status"))),
        SECTION_ORDER.get(category, 99),
        SPORT_ORDER.get(sport, 99),
        _safe_str(match.get("competition")).lower(),
        _safe_str(match.get("start_time")).lower(),
        _safe_str(match.get("home_team")).lower(),
        _safe_str(match.get("away_team")).lower(),
    )


def _build_sections(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sections_map = {
        "selecciones": {"key": "selecciones", "title": "Selecciones nacionales", "items": []},
        "ligas_locales": {"key": "ligas_locales", "title": "Ligas locales", "items": []},
        "exterior": {"key": "exterior", "title": "Argentinos en el exterior", "items": []},
        "motorsport": {"key": "motorsport", "title": "Motorsport argentino", "items": []},
    }

    for match in matches:
        tipo = clasificar_partido(match)
        if tipo and tipo in sections_map:
            match["category"] = tipo
            sections_map[tipo]["items"].append(match)

    ordered = []
    for key in ["selecciones", "ligas_locales", "exterior", "motorsport"]:
        if sections_map[key]["items"]:
            ordered.append(sections_map[key])

    return ordered


# -------------------------------------------------------------------
# Ejecución de un deporte
# -------------------------------------------------------------------

async def _run_adapter(scraper_cls: type[BaseScraper], sport: str, target_date: str) -> list[Any]:
    scraper = scraper_cls()

    try:
        return await scraper.scrape(target_date)
    except TypeError:
        pass
    except Exception:
        raise

    return await scraper.scrape()


async def run_sport(sport: str, target_date: str) -> list[dict[str, Any]]:
    cache_key = (sport, target_date)
    cached = _SPORT_CACHE.get(cache_key)
    if cached is not None:
        return deepcopy(cached)

    scraper_cls = ADAPTER_REGISTRY.get(sport)
    if scraper_cls is None:
        logger.warning(f"[registry] deporte no registrado: {sport}")
        _SPORT_CACHE[cache_key] = []
        return []

    try:
        raw_matches = await asyncio.wait_for(
            _run_adapter(scraper_cls, sport, target_date),
            timeout=SCRAPER_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.warning(f"[{sport}] TIMEOUT -> se saltea")
        _SPORT_CACHE[cache_key] = []
        return []
    except Exception as e:
        logger.exception(f"[{sport}] ERROR al scrape(): {e}")
        _SPORT_CACHE[cache_key] = []
        return []

    normalized_matches: list[dict[str, Any]] = []

    for raw_match in raw_matches or []:
        try:
            match = _normalize_match(raw_match, fallback_sport=sport)
            normalized_matches.append(match)
        except Exception as e:
            logger.warning(f"[{sport}] match descartado por error de normalización: {e}")

    normalized_matches.sort(key=_sort_key)
    _SPORT_CACHE[cache_key] = deepcopy(normalized_matches)

    logger.info(f"[{sport}] normalizados={len(normalized_matches)} date={target_date}")
    return deepcopy(normalized_matches)


# -------------------------------------------------------------------
# Resumen diario unificado
# -------------------------------------------------------------------

async def get_today_summary(target_date: str) -> dict[str, Any]:
    cached = _SUMMARY_CACHE.get(target_date)
    if cached is not None:
        return deepcopy(cached)

    all_matches: list[dict[str, Any]] = []
    by_sport_raw: dict[str, list[dict[str, Any]]] = {}

    for sport in ADAPTER_REGISTRY.keys():
        matches = await run_sport(sport, target_date)
        by_sport_raw[sport] = matches
        all_matches.extend(matches)

    # Filtramos solo lo editorialmente útil
    editorial_matches: list[dict[str, Any]] = []
    for m in all_matches:
        tipo = clasificar_partido(m)
        if tipo:
            m["category"] = tipo
            m["is_argentina_relevant"] = True
            editorial_matches.append(m)

    editorial_matches.sort(key=_sort_key)

    live = [m for m in editorial_matches if m.get("status") == "live"]
    upcoming = [m for m in editorial_matches if m.get("status") == "upcoming"]
    finished = [m for m in editorial_matches if m.get("status") == "finished"]

    sections = _build_sections(editorial_matches)
    now_arg = _now_art()

    by_sport = {}
    for m in editorial_matches:
        sport = _normalize_text(m.get("sport"))
        if sport == "football":
            sport = "futbol"
        by_sport[sport] = by_sport.get(sport, 0) + 1

    summary = {
        "date": target_date,
        "updated_at": now_arg.isoformat(),
        "matches": editorial_matches,
        "stats": {
            "live": len(live),
            "upcoming": len(upcoming),
            "finished": len(finished),
            "total": len(editorial_matches),
        },
        "summary": {
            "live": len(live),
            "upcoming": len(upcoming),
            "finished": len(finished),
            "total": len(editorial_matches),
        },
        "by_sport": by_sport,
        "sections": sections,
        "load_errors": LOAD_ERRORS,
    }

    _SUMMARY_CACHE[target_date] = deepcopy(summary)
    logger.info(
        f"[SUMMARY] date={target_date} total={len(editorial_matches)} "
        f"live={len(live)} sports={summary['by_sport']}"
    )
    return deepcopy(summary)


def clear_cache(date: str | None = None) -> None:
    if date:
        _SUMMARY_CACHE.pop(date, None)
        for key in list(_SPORT_CACHE.keys()):
            if key[1] == date:
                _SPORT_CACHE.pop(key, None)
        logger.info(f"[registry] cache limpiado para {date}")
        return

    _SUMMARY_CACHE.clear()
    _SPORT_CACHE.clear()
    logger.info("[registry] cache completo limpiado")
