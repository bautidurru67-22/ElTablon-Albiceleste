"""
/api/hoy — agenda unificada del día.
Lee cache del agregador. Nunca scrapea directo.
"""
from fastapi import APIRouter
from app.services.match_service import (
    get_hoy,
    get_futbol_hoy,
    get_futbol_live,
    get_tenis_hoy,
    get_basquet_hoy,
    get_rugby_hoy,
    get_hockey_hoy,
    get_sport_hoy,
)

router = APIRouter()


@router.get("")
async def hoy():
    """
    Agenda completa: en_vivo / proximos / finalizados.
    Todos los deportes, con relevancia argentina.
    """
    return await get_hoy()


@router.get("/futbol")
async def futbol_hoy():
    return await get_futbol_hoy()


@router.get("/futbol/live")
async def futbol_live():
    return await get_futbol_live()


@router.get("/tenis")
async def tenis_hoy():
    return await get_tenis_hoy()


@router.get("/basquet")
async def basquet_hoy():
    return await get_basquet_hoy()


@router.get("/rugby")
async def rugby_hoy():
    return await get_rugby_hoy()


@router.get("/hockey")
async def hockey_hoy():
    return await get_hockey_hoy()


@router.get("/{sport}")
async def sport_hoy(sport: str):
    """Genérico: /api/hoy/voley, /api/hoy/golf, etc."""
    return await get_sport_hoy(sport)
