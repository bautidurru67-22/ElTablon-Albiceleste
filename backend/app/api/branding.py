from fastapi import APIRouter
from app.config import settings

router = APIRouter()

@router.get("")
async def get_branding_assets():
    return {
        "logo_url": settings.branding_logo_url,
        "banner_url": settings.branding_banner_url,
    }
