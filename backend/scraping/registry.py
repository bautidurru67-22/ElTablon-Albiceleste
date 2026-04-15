"""
Registry central de adapters + agregador Argentina-first para El Tablón Albiceleste.

Versión endurecida:
- elimina falsos positivos de clubes argentinos
- clasifica mejor fútbol
- mantiene cache por día
- construye sections para /api/hoy y /api/calendario
"""

from __future__ import annotations

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

LOAD_ERRORS: dict[str, str] = {}

_SUMMARY_CACHE: dict[str, dict[str, Any]] = {}
_SPORT_CACHE: dict[tuple[str, str], list[dict[str, Any]]] = {}


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
    "exterior": 1,
    "ligas_locales": 2,
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

ARGENTINA_SELECTION_ALIASES = {
    "argentina",
    "seleccion argentina",
    "argentina sub 17",
    "argentina sub 20",
    "argentina sub 23",
    "argentina u17",
    "argentina u20",
    "argentina u23",
    "argentina women",
    "argentina femenino",
    "argentina femenina",
    "argentina women national team",
}

# Alias exactos controlados.
# Acá evitamos nombres demasiado genéricos como "arsenal", "union", "barracas".
ARGENTINE_CLUB_ALIASES = {
    "argentinos juniors",
    "atletico tucuman",
    "aldosivi",
    "arsenal de sarandi",
    "arsenal sarandi",
    "banfield",
    "barracas central",
    "belgrano",
    "boca juniors",
    "central cordoba",
    "central cordoba sdE",
    "central cordoba sde",
    "chacarita juniors",
    "colon",
    "colon de santa fe",
    "defensa y justicia",
    "deportivo riestra",
    "estudiantes",
    "estudiantes de la plata",
    "ferro",
    "ferro carril oeste",
    "gimnasia",
    "gimnasia y esgrima la plata",
    "godoy cruz",
    "huracan",
    "independiente",
    "independiente rivadavia",
    "instituto",
    "lanus",
    "newells old boys",
    "newells",
    "newells",
    "newell's old boys",
    "platense",
    "quilmes",
    "racing",
    "racing club",
    "river plate",
    "rosario central",
    "san lorenzo",
    "san martin de tucuman",
    "san martin tucuman",
    "san martin de san juan",
    "sarmiento",
    "talleres",
    "talleres de cordoba",
    "tigre",
    "union de santa fe",
    "union santa fe",
    "velez",
    "velez sarsfield",
}

LOCAL_COMPETITION_PATTERNS = [
    "liga profesional",
    "copa de la liga",
    "primera nacional",
    "primera b",
    "primera c",
    "federal a",
    "torneo federal",
    "copa argentina",
    "supercopa argentina",
    "reserva",
    "liga argentina",
    "liga nacional",
    "lnb",
    "urba",
    "top 12",
    "metropolitano",
    "torneo del interior",
    "liga de voley argentina",
    "liga de vóley argentina",
    "lnv",
    "liga de futsal afa",
    "afa futsal",
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


def _now_art() -> datetime:
    return datetime.now(ART_TZ)


def _safe_str(value: Any) -> str:
    return "" if value is None else str(value).strip()


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


def _canonicalize_team_name(name: str) -> str:
    text = _normalize_text(name)

    replacements = {
        "ca ": "",
        "c a ": "",
        "fc ": "",
        "sc ": "",
        "club atletico ": "",
        "club atletico": "",
        "club ": "",
        "deportivo ": "deportivo ",
        "atletico ": "atletico ",
    }

    for old, new in replacements.items():
        if text.startswith(old):
            text = (new + text[len(old):]).strip()

    text = re.sub(r"\s+", " ", text).strip()
    return text


def _is_selection_name(name: str) -> bool:
    text = _canonicalize_team_name(name)
    if text in ARGENTINA_SELECTION_ALIASES:
        return True
    return text.startswith("argentina ")


def _is_argentine_club(name: str) -> bool:
    text = _canonicalize_team_name(name)

    if not text:
        return False

    if text in ARGENTINE_CLUB_ALIASES:
        return True

    exact_alias_map = {
        "racing club avellaneda": "racing club",
        "club atletico river plate": "river plate",
        "club atletico boca juniors": "boca juniors",
        "club atletico independiente": "independiente",
        "club atletico rosario central": "rosario central",
        "club atletico tigre": "tigre",
        "club atletico lanus": "lanus",
        "club atletico huracan": "huracan",
        "club atletico belgrano": "belgrano",
        "club atletico banfield": "banfield",
        "club atletico union": "union de santa fe",
        "club atletico talleres": "talleres",
        "club atletico san lorenzo": "san lorenzo",
        "club atletico velez sarsfield": "velez sarsfield",
    }

    mapped = exact_alias_map.get(text)
    if mapped and mapped in ARGENTINE_CLUB_ALIASES:
        return True

    return False


def _is_local_competition(name: str) -> bool:
    text = _normalize_text(name)
    if not text:
        return False
    return any(pattern in text for pattern in LOCAL_COMPETITION_PATTERNS)


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


def _classify_football(match: dict[str, Any]) -> tuple[bool, str, str, list[str]]:
    home = _safe_str(match.get("home_team"))
    away = _safe_str(match.get("away_team"))
    competition = _safe_str(match.get("competition"))

    entities: list[str] = []

    if _is_selection_name(home) or _is_selection_name(away):
        if home:
            entities.append(home)
        if away:
            entities.append(away)
        return True, "selecciones", "seleccion", entities

    if _is_local_competition(competition):
        if home:
            entities.append(home)
        if away:
            entities.append(away)
        return True, "ligas_locales", "liga_local", entities

    home_is_arg = _is_argentine_club(home)
    away_is_arg = _is_argentine_club(away)

    if home_is_arg or away_is_arg:
        if home_is_arg:
            entities.append(home)
        if away_is_arg:
            entities.append(away)
        return True, "exterior", "equipo_argentino", entities

    return False, "", "", []


def _classify_non_football(match: dict[str, Any], sport: str) -> tuple[bool, str, str, list[str]]:
    if sport in {"motorsport", "motogp", "dakar"}:
        if _is_motorsport_argentina_related(match):
            entities = []
            if match.get("home_team"):
                entities.append(_safe_str(match["home_team"]))
            if match.get("away_team"):
                entities.append(_safe_str(match["away_team"]))
            return True, "motorsport", "motor_arg", entities
        return False, "", "", []

    existing_reason = _safe_str(match.get("argentina_reason"))
    if existing_reason:
        return True, "exterior", existing_reason, match.get("argentina_entities", []) or []

    return False, "", "", []


def _classify_match(match: dict[str, Any]) -> dict[str, Any] | None:
    sport = _normalize_text(match.get("sport"))

    if sport == "football":
        sport = "futbol"
        match["sport"] = "futbol"

    if sport == "basketball":
        sport = "basquet"
        match["sport"] = "basquet"

    if sport == "volleyball":
        sport = "voley"
        match["sport"] = "voley"

    if sport in {"futbol", "soccer"}:
        is_relevant, category, reason, entities = _classify_football(match)
    else:
        is_relevant, category, reason, entities = _classify_non_football(match, sport)

    if not is_relevant:
        return None

    match["category"] = category
    match["argentina_reason"] = reason
    match["argentina_entities"] = entities
    match["is_argentina_relevant"] = True
    return match


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
        "exterior": {"key": "exterior", "title": "Argentinos en el exterior", "items": []},
        "ligas_locales": {"key": "ligas_locales", "title": "Ligas locales", "items": []},
        "motorsport": {"key": "motorsport", "title": "Motorsport argentino", "items": []},
    }

    for match in matches:
        key = match.get("category")
        if key in sections_map:
            sections_map[key]["items"].append(match)

    ordered = []
    for key in ["selecciones", "exterior", "ligas_locales", "motorsport"]:
        if sections_map[key]["items"]:
            ordered.append(sections_map[key])

    return ordered


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
        raw_matches = await _run_adapter(scraper_cls, sport, target_date)
    except Exception as e:
        logger.exception(f"[{sport}] ERROR al scrape(): {e}")
        _SPORT_CACHE[cache_key] = []
        return []

    normalized_matches: list[dict[str, Any]] = []

    for raw_match in raw_matches or []:
        try:
            match = _normalize_match(raw_match, fallback_sport=sport)
            classified = _classify_match(match)
            if classified is not None:
                normalized_matches.append(classified)
        except Exception as e:
            logger.warning(f"[{sport}] match descartado por error de normalización: {e}")

    normalized_matches.sort(key=_sort_key)
    _SPORT_CACHE[cache_key] = deepcopy(normalized_matches)
    logger.info(f"[{sport}] relevantes={len(normalized_matches)} date={target_date}")
    return deepcopy(normalized_matches)


async def get_today_summary(target_date: str) -> dict[str, Any]:
    cached = _SUMMARY_CACHE.get(target_date)
    if cached is not None:
        return deepcopy(cached)

    all_matches: list[dict[str, Any]] = []
    by_sport: dict[str, list[dict[str, Any]]] = {}

    for sport in ADAPTER_REGISTRY.keys():
        matches = await run_sport(sport, target_date)
        by_sport[sport] = matches
        all_matches.extend(matches)

    all_matches.sort(key=_sort_key)

    live = [m for m in all_matches if m.get("status") == "live"]
    upcoming = [m for m in all_matches if m.get("status") == "upcoming"]
    finished = [m for m in all_matches if m.get("status") == "finished"]

    sections = _build_sections(all_matches)
    now_arg = _now_art()

    summary = {
        "date": target_date,
        "updated_at": now_arg.isoformat(),
        "matches": all_matches,
        "stats": {
            "live": len(live),
            "upcoming": len(upcoming),
            "finished": len(finished),
            "total": len(all_matches),
        },
        "summary": {
            "live": len(live),
            "upcoming": len(upcoming),
            "finished": len(finished),
            "total": len(all_matches),
        },
        "by_sport": {sport: len(matches) for sport, matches in by_sport.items() if matches},
        "sections": sections,
        "load_errors": LOAD_ERRORS,
    }

    _SUMMARY_CACHE[target_date] = deepcopy(summary)
    logger.info(
        f"[SUMMARY] date={target_date} total={len(all_matches)} "
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
