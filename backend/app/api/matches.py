from fastapi import APIRouter, Query
from scraping.registry import get_today_summary

router = APIRouter()


@router.get("/live")
async def get_live(sport: str | None = Query(None, description="Filtrar por deporte")):
    summary = await get_today_summary()

    matches = summary.get("matches", [])
    live_matches = [m for m in matches if m.get("status") == "live"]

    if sport:
        live_matches = [m for m in live_matches if m.get("sport") == sport]

    return live_matches


@router.get("/today")
async def get_today(sport: str | None = Query(None, description="Filtrar por deporte")):
    summary = await get_today_summary()

    matches = summary.get("matches", [])

    if sport:
        matches = [m for m in matches if m.get("sport") == sport]

    return matches


@router.get("/results")
async def get_results(sport: str | None = Query(None, description="Filtrar por deporte")):
    summary = await get_today_summary()

    matches = summary.get("matches", [])
    finished_matches = [m for m in matches if m.get("status") == "finished"]

    if sport:
        finished_matches = [m for m in finished_matches if m.get("sport") == sport]

    return finished_matches


@router.get("/argentina")
async def get_argentina(sport: str | None = Query(None, description="Filtrar por deporte")):
    summary = await get_today_summary()

    matches = summary.get("matches", [])
    argentina_matches = [
        m for m in matches
        if m.get("argentina_relevance") in ("seleccion", "club_arg", "jugador_arg")
    ]

    if sport:
        argentina_matches = [m for m in argentina_matches if m.get("sport") == sport]

    return argentina_matches


@router.get("/club")
async def get_club(
    club: str = Query(..., description="Nombre del club"),
    sport: str | None = Query(None, description="Filtrar por deporte"),
):
    summary = await get_today_summary()

    matches = summary.get("matches", [])
    club_lower = club.lower().strip()

    club_matches = [
        m for m in matches
        if club_lower in (m.get("home_team", "").lower() or "")
        or club_lower in (m.get("away_team", "").lower() or "")
    ]

    if sport:
        club_matches = [m for m in club_matches if m.get("sport") == sport]

    return club_matches
