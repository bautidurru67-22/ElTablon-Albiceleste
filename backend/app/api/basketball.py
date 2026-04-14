from fastapi import APIRouter, Query

from app.services.basketball_service import get_lnb_overview

router = APIRouter()


@router.get('/overview')
async def basketball_overview(
    competition: str = Query('liga-nacional', description='Torneo/división a mostrar')
):
    return await get_lnb_overview(competition=competition)
