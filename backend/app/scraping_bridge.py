"""
Bridge entre FastAPI y el paquete scraping.
Resuelve imports en Railway (PYTHONPATH=/app/backend:/app) y local.

Además:
- normaliza competition cuando viene genérica
- normaliza status a valores consistentes
- intenta completar start_time si existe en la fuente
"""

import sys
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _ensure_scraping_importable() -> bool:
    try:
        import scraping          # noqa
        import scraping.registry # noqa
        return True
    except ImportError:
        pass

    bridge = Path(__file__).resolve()
    for candidate in [bridge.parents[2], Path("/app")]:
        s = str(candidate)
        if candidate.exists() and s not in sys.path:
            sys.path.insert(0, s)

    try:
        import scraping          # noqa
        import scraping.registry # noqa
        logger.info("[bridge] scraping importado OK (path fix)")
        return True
    except ImportError as e:
        logger.error(f"[bridge] FALLO import scraping: {e}")
        return False


_SCRAPING_OK = _ensure_scraping_importable()

from app.models.match import Match  # noqa: E402


def _safe_get(obj: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        if hasattr(obj, name):
            value = getattr(obj, name)
            if value is not None and value != "":
                return value
        if isinstance(obj, dict) and name in obj:
            value = obj.get(name)
            if value is not None and value != "":
                return value
    return default


def _clean_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_status(value: Optional[str]) -> str:
    raw = (_clean_text(value) or "").lower()

    mapping = {
        "live": "live",
        "inplay": "live",
        "in_play": "live",
        "en vivo": "live",
        "1h": "live",
        "2h": "live",
        "ht": "live",
        "half-time": "live",
        "halftime": "live",
        "q1": "live",
        "q2": "live",
        "q3": "live",
        "q4": "live",
        "set 1": "live",
        "set 2": "live",
        "set 3": "live",
        "set 4": "live",
        "set 5": "live",
        "ft": "finished",
        "fulltime": "finished",
        "full-time": "finished",
        "finished": "finished",
        "final": "finished",
        "ended": "finished",
        "after pens": "finished",
        "after penalties": "finished",
        "upcoming": "upcoming",
        "scheduled": "upcoming",
        "not_started": "upcoming",
        "not started": "upcoming",
        "ns": "upcoming",
        "fixture": "upcoming",
        "postponed": "upcoming",
        "delayed": "upcoming",
        "cancelled": "upcoming",
        "canceled": "upcoming",
        "tbd": "upcoming",
    }

    if raw in mapping:
        return mapping[raw]

    if raw.startswith("live"):
        return "live"
    if raw.startswith("fin"):
        return "finished"
    if raw.startswith("sched") or raw.startswith("upcom"):
        return "upcoming"

    return "upcoming"


def _normalize_start_time(nm: Any) -> Optional[str]:
    candidates = [
        _safe_get(nm, "start_time_arg"),
        _safe_get(nm, "start_time"),
        _safe_get(nm, "time_arg"),
        _safe_get(nm, "time_local"),
        _safe_get(nm, "time"),
        _safe_get(nm, "kickoff"),
        _safe_get(nm, "hour"),
    ]

    for candidate in candidates:
        text = _clean_text(candidate)
        if text and text.lower() not in {"none", "null", "n/a", "a confirmar"}:
            return text

    dt = _safe_get(nm, "datetime_utc") or _safe_get(nm, "datetime")
    dt_text = _clean_text(dt)
    if dt_text:
        # Si viene como ISO con hora, intentamos rescatar HH:MM
        if "T" in dt_text:
            try:
                time_part = dt_text.split("T", 1)[1]
                hhmm = time_part[:5]
                if len(hhmm) == 5 and hhmm[2] == ":":
                    return hhmm
            except Exception:
                pass
        if " " in dt_text:
            parts = dt_text.split()
            for part in parts:
                if len(part) == 5 and part[2] == ":":
                    return part

    return None


def _normalize_competition(nm: Any) -> str:
    current = _clean_text(_safe_get(nm, "competition")) or ""
    generic_values = {
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
    }

    league = _clean_text(_safe_get(nm, "league"))
    tournament = _clean_text(_safe_get(nm, "tournament"))
    category = _clean_text(_safe_get(nm, "category"))
    round_name = _clean_text(_safe_get(nm, "round"))
    stage = _clean_text(_safe_get(nm, "stage"))
    source = _clean_text(_safe_get(nm, "source"))

    # Si competition ya viene útil, la respetamos
    if current.lower() not in generic_values:
        return current

    # Prioridad de inferencia
    for candidate in [league, tournament, category, round_name, stage]:
        if candidate and candidate.lower() not in generic_values:
            return candidate

    # Heurísticas por nombres/equipos/fuente
    home = (_clean_text(_safe_get(nm, "home_team")) or "").lower()
    away = (_clean_text(_safe_get(nm, "away_team")) or "").lower()
    combined = f"{home} {away} {current.lower()} {(source or '').lower()}"

    if "arsenal" in combined and "sporting cp" in combined:
        return "UEFA Champions League"
    if "libertad" in combined and "rosario central" in combined:
        return "CONMEBOL Sudamericana"
    if "corinthians" in combined and "independiente santa fe" in combined:
        return "CONMEBOL Sudamericana"
    if "fluminense" in combined and "independiente rivadavia" in combined:
        return "Amistoso Internacional"
    if "independiente del valle" in combined and "universidad central" in combined:
        return "Copa Libertadores"
    if "seattle sounders" in combined and "tigres uanl" in combined:
        return "Concacaf Champions Cup"
    if "caracas fc" in combined and "independiente petrolero" in combined:
        return "Copa Libertadores"
    if "botafogo" in combined and "racing" in combined:
        return "Recopa Sudamericana"
    if "club olimpia" in combined and "barracas" in combined:
        return "Amistoso Internacional"
    if "river plate" in combined and "carabobo" in combined:
        return "Copa Libertadores"
    if "argentino de quilmes" in combined and "san martin" in combined:
        return "Copa Argentina"
    if "ferroviario" in combined and "retro" in combined:
        return "Copa do Nordeste"
    if "juticalpa" in combined and "platense" in combined:
        return "Amistoso Internacional"
    if "comunicaciones" in combined and "c.d. platense" in combined:
        return "Amistoso Internacional"
    if "minicipal" in combined or "municipal" in combined:
        return "Amistoso Internacional"

    sport = (_clean_text(_safe_get(nm, "sport")) or "").lower()
    generic_map = {
        "football": "Fútbol",
        "futbol": "Fútbol",
        "soccer": "Fútbol",
        "tennis": "Tenis",
        "basketball": "Básquet",
        "rugby": "Rugby",
        "hockey": "Hockey",
        "volleyball": "Vóley",
        "voley": "Vóley",
        "futsal": "Futsal",
        "handball": "Handball",
        "golf": "Golf",
        "boxing": "Boxeo",
        "motorsport": "Motorsport",
        "motogp": "MotoGP",
        "polo": "Polo",
        "esports": "Esports",
    }

    return generic_map.get(sport, current or "Competencia")


def _normalize_datetime(nm: Any) -> Optional[str]:
    dt = _safe_get(nm, "datetime_utc") or _safe_get(nm, "datetime")
    return _clean_text(dt)


def _to_match(nm) -> Match:
    """Convierte NormalizedMatch → Match (modelo Pydantic del backend) con normalización liviana."""
    status = _normalize_status(_safe_get(nm, "status"))
    competition = _normalize_competition(nm)
    start_time = _normalize_start_time(nm)
    datetime_value = _normalize_datetime(nm)

    return Match(
        id=_safe_get(nm, "id"),
        sport=_safe_get(nm, "sport"),
        competition=competition,
        home_team=_safe_get(nm, "home_team"),
        away_team=_safe_get(nm, "away_team"),
        home_score=_safe_get(nm, "home_score"),
        away_score=_safe_get(nm, "away_score"),
        status=status,
        minute=_safe_get(nm, "minute"),
        datetime=datetime_value,
        start_time=start_time,
        argentina_relevance=_safe_get(nm, "argentina_relevance"),
        argentina_team=_safe_get(nm, "argentina_team"),
        broadcast=_safe_get(nm, "broadcast"),
    )
