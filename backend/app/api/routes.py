from fastapi import APIRouter
from app.api import matches, sports, players, health, auth, favorites

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(favorites.router, prefix="/favorites", tags=["favorites"])
router.include_router(matches.router, prefix="/matches", tags=["matches"])
router.include_router(sports.router, prefix="/sports", tags=["sports"])
router.include_router(players.router, prefix="/players", tags=["players"])
router.include_router(health.router, tags=["health"])
