from fastapi import APIRouter, HTTPException
from app.services.competition_service import (
    list_competitions,
    get_competition_fixture,
    get_competition_table,
    get_competition_scorers,
    COMPETITION_MAP,
)

router = APIRouter()


def _validate(sport: str, slug: str | None = None) -> None:
    if sport not in COMPETITION_MAP:
        raise HTTPException(status_code=404, detail=f"Deporte no soportado: {sport}")
    if slug is not None and slug not in COMPETITION_MAP[sport]:
        raise HTTPException(status_code=404, detail=f"Competencia no soportada: {sport}/{slug}")


@router.get("/{sport}")
async def competitions_by_sport(sport: str):
    _validate(sport)
    return await list_competitions(sport)


@router.get("/{sport}/{slug}/fixture")
async def competition_fixture(sport: str, slug: str):
    _validate(sport, slug)
    return await get_competition_fixture(sport, slug)


@router.get("/{sport}/{slug}/table")
async def competition_table(sport: str, slug: str):
    _validate(sport, slug)
    return await get_competition_table(sport, slug)


@router.get("/{sport}/{slug}/scorers")
async def competition_scorers(sport: str, slug: str):
    _validate(sport, slug)
    return await get_competition_scorers(sport, slug)
