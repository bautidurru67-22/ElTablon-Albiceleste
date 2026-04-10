from fastapi import APIRouter
from app.services.sport_service import get_sports_summary

router = APIRouter()


@router.get("/")
async def sports_list():
    """Lista de deportes con cantidad de eventos activos hoy."""
    return await get_sports_summary()
