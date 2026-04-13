from fastapi import APIRouter, Query
from app.models.match import Match
from app.services.match_service import (
    get_live_matches,
    get_today_matches,
    get_results_matches,
    get_argentina_matches,
    get_club_matches,
)

router = APIRouter()


@router.get("/live", response_model=list[Match])
async def live_matches(sport: str | None = Query(None, description="Filtrar por deporte")):
    """Partidos en vivo. Filtrable por deporte."""
    return await get_live_matches(sport=sport)


@router.get("/today", response_model=list[Match])
async def today_matches(sport: str | None = Query(None)):
    """Todos los partidos del día (live → upcoming → finished)."""
    return await get_today_matches(sport=sport)


@router.get("/results", response_model=list[Match])
async def results_matches(sport: str | None = Query(None)):
    """Resultados finalizados del día."""
    return await get_results_matches(sport=sport)


@router.get("/argentina", response_model=list[Match])
async def argentina_matches():
    """Partidos con relevancia argentina, ordenados live → upcoming → finished."""
    return await get_argentina_matches()


@router.get("/club/{club_id}", response_model=list[Match])
async def club_matches(club_id: str):
    """Partidos de un club específico (para Club view)."""
    return await get_club_matches(club_id=club_id)
