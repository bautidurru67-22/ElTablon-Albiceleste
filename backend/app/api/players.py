from fastapi import APIRouter
from app.services.player_service import get_argentines_abroad

router = APIRouter()


@router.get("/abroad")
async def players_abroad():
    """Jugadores argentinos compitiendo en el exterior hoy."""
    return await get_argentines_abroad()
