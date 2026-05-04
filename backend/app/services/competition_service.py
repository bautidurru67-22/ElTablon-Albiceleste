from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Any
import unicodedata

from app.services.football_service import get_football_overview
from app.services.basketball_service import get_lnb_overview
from app.cache import cache

AR_TZ = ZoneInfo("America/Argentina/Buenos_Aires")

COMPETITION_MAP: dict[str, dict[str, dict[str, Any]]] = {
    "futbol": {
        "liga-profesional-argentina": {
            "label": "Liga Profesional",
            "keywords": ["liga profesional", "lpf", "superliga", "primera división"],
        },
        "primera-nacional": {"label": "Primera Nacional", "keywords": ["primera nacional"]},
        "b-metro": {"label": "B Metro", "keywords": ["b metro", "primera b"]},
        "primera-c": {"label": "Primera C", "keywords": ["primera c"]},
        "federal-a": {"label": "Federal A", "keywords": ["federal a"]},
        "copa-argentina": {"label": "Copa Argentina", "keywords": ["copa argentina"]},
        "libertadores": {"label": "Copa Libertadores", "keywords": ["libertadores"]},
        "sudamericana": {"label": "Copa Sudamericana", "keywords": ["sudamericana"]},
    },
    "basquet": {
        "liga-nacional": {"label": "Liga Nacional", "keywords": ["liga nacional", "lnb"]},
        "liga-argentina": {"label": "Liga Argentina", "keywords": ["liga argentina"]},
        "liga-federal": {"label": "Liga Federal", "keywords": ["liga federal"]},
    },
}

COMPETITION_ALIASES = {"futbol": {"liga-profesional": "liga-profesional-argentina"}}


def resolve_competition_slug(sport: str, slug: str) -> str:
    return COMPETITION_ALIASES.get(sport, {}).get(slug, slug)


def _norm(s: str | None) -> str:
    s = (s or "").strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return s


def _to_arg_datetime(value: str | None) -> str | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.astimezone(AR_TZ).isoformat()
    except Exception:
        return value


def _map_status(status: str | None) -> str:
    s = (status or "").lower()
    mp = {
        "upcoming": "programado",
        "scheduled": "programado",
        "ns": "programado",
        "tbd": "programado",
        "pst": "postergado",
        "postponed": "postergado",
        "live": "en_vivo",
        "1h": "en_vivo",
        "ht": "en_vivo",
        "2h": "en_vivo",
        "et": "en_vivo",
        "finished": "finalizado",
        "ft": "finalizado",
        "aet": "finalizado",
        "pen": "finalizado",
        "suspended": "suspendido",
        "abd": "suspendido",
    }
    return mp.get(s, s or "programado")


def _status_from_match_obj(status: str | None) -> str:
    s = (status or "").lower()
    if s == "live":
        return "en_vivo"
    if s == "finished":
        return "finalizado"
    return "programado"


def _build_fixtures_from_match_cache(sport: str, slug: str, competition_label: str) -> list[dict]:
    """
    Fallback real (no mock) usando cache today:{sport} llenado por scrapers.
    """
    raw = cache._store.get(f"today:{sport}") if hasattr(cache, "_store") else None
    if raw is None:
        return []

    items = raw if isinstance(raw, list) else []
    keywords = COMPETITION_MAP.get(sport, {}).get(slug, {}).get("keywords", [])
    k_norm = [_norm(k) for k in keywords]

    filtered = []
    for m in items:
        comp = _norm(getattr(m, "competition", "") or "")
        if k_norm and not any(k in comp for k in k_norm):
            continue
        filtered.append(m)

    fixtures = []
    for i, m in enumerate(filtered):
        fixtures.append(
            {
                "id": f"{sport}-{slug}-cache-{i}",
                "sport": sport,
                "competition": getattr(m, "competition", None) or competition_label,
                "round": None,
                "group": None,
                "home_team": getattr(m, "home_team", None),
                "away_team": getattr(m, "away_team", None),
                "home_logo": None,
                "away_logo": None,
                "home_score": getattr(m, "home_score", None),
                "away_score": getattr(m, "away_score", None),
                "status": _status_from_match_obj(getattr(m, "status", None)),
                "datetime_arg": _to_arg_datetime(getattr(m, "start_time", None)),
                "venue": None,
                "source": getattr(m, "source", None) or "cache_today",
                "match_url": None,
            }
        )

    return fixtures


async def list_competitions(sport: str) -> dict:
    return {
        "sport": sport,
        "items": [
            {"slug": k, "label": v["label"]}
            for k, v in COMPETITION_MAP.get(sport, {}).items()
        ],
    }


def _normalize_standings(rows: list[dict]) -> list[dict]:
    standings = []
    for r in rows:
        standings.append(
            {
                "position": r.get("position") or len(standings) + 1,
                "team_name": r.get("team"),
                "team_logo": r.get("team_logo"),
                "played": r.get("played") or r.get("pj"),
                "won": r.get("won"),
                "drawn": r.get("drawn"),
                "lost": r.get("lost"),
                "points": r.get("points") or r.get("pts"),
                "goals_for": r.get("goals_for"),
                "goals_against": r.get("goals_against"),
                "goal_difference": r.get("goal_diff"),
                "recent_results": r.get("form"),
                "group": r.get("group_name"),
                "percentage": r.get("percentage"),
                "points_for": r.get("points_for"),
                "points_against": r.get("points_against"),
                "difference": r.get("difference"),
                "conference": r.get("conference"),
            }
        )
    return standings


def _normalize_fixtures(sport: str, slug: str, raw: dict) -> list[dict]:
    fixtures = []
    for i, f in enumerate(raw.get("fixtures", [])):
        fixtures.append(
            {
                "id": f"{sport}-{slug}-{i}",
                "sport": sport,
                "competition": raw.get("competition_label"),
                "round": f.get("round"),
                "group": f.get("group"),
                "home_team": f.get("home"),
                "away_team": f.get("away"),
                "home_logo": f.get("home_logo"),
                "away_logo": f.get("away_logo"),
                "home_score": f.get("home_score"),
                "away_score": f.get("away_score"),
                "status": _map_status(f.get("status")),
                "datetime_arg": _to_arg_datetime(f.get("date") or f.get("start_time")),
                "venue": f.get("venue"),
                "source": raw.get("source"),
                "match_url": f.get("match_url"),
            }
        )
    return fixtures


async def get_competition_overview(sport: str, slug: str) -> dict:
    slug = resolve_competition_slug(sport, slug)
    attempted: list[str] = []
    source_used = None

    competition_label = (
        COMPETITION_MAP.get(sport, {}).get(slug, {}).get("label", slug.replace("-", " ").title())
    )

    raw = {
        "standings": [],
        "fixtures": [],
        "competition_label": competition_label,
    }

    if sport == "futbol":
        attempted = ["liga_profesional", "promiedos", "espn", "api_football", "sofascore", "cache_today"]
        raw = await get_football_overview(slug)
        if raw.get("standings") or raw.get("fixtures"):
            source_used = raw.get("source") or "api_football"

    elif sport == "basquet":
        attempted = ["liga_nacional", "liga_argentina", "quinto_cuarto", "sofascore", "365scores", "cache_today"]
        raw = await get_lnb_overview(slug)
        if raw.get("standings") or raw.get("fixtures"):
            source_used = raw.get("source") or "lnb"

    standings = _normalize_standings(raw.get("standings", []))
    fixtures = _normalize_fixtures(sport, slug, raw)

    # Fallback REAL si la fuente principal no trae fixtures
    if not fixtures:
        fallback_fixtures = _build_fixtures_from_match_cache(sport, slug, competition_label)
        if fallback_fixtures:
            fixtures = fallback_fixtures
            source_used = source_used or "cache_today"

    return {
        "sport": sport,
        "competition": raw.get("competition_label") or competition_label,
        "season": datetime.now().year,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source_used": source_used,
        "sources_attempted": attempted,
        "standings": standings,
        "fixtures": fixtures,
        "groups": [],
        "error": None if (standings or fixtures) else "No hay datos disponibles para esta competencia",
    }


async def get_competition_fixture(sport: str, slug: str) -> dict:
    data = await get_competition_overview(sport, slug)
    return {
        k: data[k]
        for k in [
            "sport",
            "competition",
            "updated_at",
            "source_used",
            "sources_attempted",
            "fixtures",
            "error",
        ]
    }


async def get_competition_table(sport: str, slug: str) -> dict:
    data = await get_competition_overview(sport, slug)
    return {
        k: data[k]
        for k in [
            "sport",
            "competition",
            "updated_at",
            "source_used",
            "sources_attempted",
            "standings",
            "error",
        ]
    }


async def get_competition_scorers(sport: str, slug: str) -> dict:
    return {"sport": sport, "slug": slug, "rows": []}
