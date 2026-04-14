from fastapi import APIRouter, Query

from app.services.football_service import get_football_overview

router = APIRouter()


@router.get('/overview')
async def football_overview(
    competition: str = Query('liga-profesional', description='Competencia de fútbol a mostrar')
):
    return await get_football_overview(competition=competition)
