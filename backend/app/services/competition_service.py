from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Any

from app.services.football_service import get_football_overview
from app.services.basketball_service import get_lnb_overview

AR_TZ = ZoneInfo("America/Argentina/Buenos_Aires")

COMPETITION_MAP: dict[str, dict[str, dict[str, Any]]] = {
    "futbol": {
        "liga-profesional-argentina": {"label": "Liga Profesional"},
        "primera-nacional": {"label": "Primera Nacional"},
        "b-metro": {"label": "B Metro"},
        "primera-c": {"label": "Primera C"},
        "federal-a": {"label": "Federal A"},
        "copa-argentina": {"label": "Copa Argentina"},
        "libertadores": {"label": "Copa Libertadores"},
        "sudamericana": {"label": "Copa Sudamericana"},
    },
    "basquet": {
        "liga-nacional": {"label": "Liga Nacional"},
        "liga-argentina": {"label": "Liga Argentina"},
        "liga-federal": {"label": "Liga Federal"},
    },
}

COMPETITION_ALIASES = {"futbol": {"liga-profesional": "liga-profesional-argentina"}}


def resolve_competition_slug(sport: str, slug: str) -> str:
    return COMPETITION_ALIASES.get(sport, {}).get(slug, slug)


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
        "live": "en_vivo",
        "finished": "finalizado",
        "suspended": "suspendido",
        "postponed": "postergado",
    }
    return mp.get(s, s or "programado")


async def list_competitions(sport: str) -> dict:
    return {
        "sport": sport,
        "items": [
            {"slug": k, "label": v["label"]}
            for k, v in COMPETITION_MAP.get(sport, {}).items()
        ],
    }


async def get_competition_overview(sport: str, slug: str) -> dict:
    slug = resolve_competition_slug(sport, slug)
    attempted: list[str] = []
    source_used = None
    raw = {
        "standings": [],
        "fixtures": [],
        "competition_label": COMPETITION_MAP.get(sport, {}).get(slug, {}).get("label", slug),
    }

    if sport == "futbol":
        attempted = ["liga_profesional", "promiedos", "espn", "api_football", "sofascore"]
        raw = await get_football_overview(slug)
        if raw.get("standings") or raw.get("fixtures"):
            source_used = raw.get("source") or "api_football"
    elif sport == "basquet":
        attempted = ["liga_nacional", "liga_argentina", "quinto_cuarto", "sofascore", "365scores"]
        raw = await get_lnb_overview(slug)
        if raw.get("standings") or raw.get("fixtures"):
            source_used = raw.get("source") or "lnb"

    standings = []
    for r in raw.get("standings", []):
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

    return {
        "sport": sport,
        "competition": raw.get("competition_label"),
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
