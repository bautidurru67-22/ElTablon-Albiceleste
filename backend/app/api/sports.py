from fastapi import APIRouter
from app.services.sport_service import get_sports_summary

router = APIRouter(prefix="/sports", tags=["sports"])


@router.get("/")
async def sports_summary():
    return await get_sports_summary()
