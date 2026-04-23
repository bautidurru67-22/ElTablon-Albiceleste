from fastapi import APIRouter

from app.api import matches, health, auth, favorites, competitions
from api_hoy import router as hoy_router

router = APIRouter()

# Endpoints agregados Argentina-first
router.include_router(hoy_router)

# Endpoints existentes
router.include_router(health.router, tags=["health"])
router.include_router(matches.router, prefix="/matches", tags=["matches"])
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(favorites.router, prefix="/favorites", tags=["favorites"])
router.include_router(competitions.router, prefix="/competitions", tags=["competitions"])

# Importaciones opcionales (no rompen si fallan)
try:
    from app.api import branding
    router.include_router(branding.router, prefix="/branding", tags=["branding"])
except Exception:
    pass

try:
    from app.api import sports
    router.include_router(sports.router, prefix="/sports", tags=["sports"])
except Exception:
    pass

try:
    from app.api import sources
    router.include_router(sources.router, prefix="/sources", tags=["sources"])
except Exception:
    pass

try:
    from app.api import football
    router.include_router(football.router, prefix="/football", tags=["football"])
except Exception:
    pass

try:
    from app.api import basketball
    router.include_router(basketball.router, prefix="/basketball", tags=["basketball"])
except Exception:
    pass

try:
    from app.api import players
    router.include_router(players.router, prefix="/players", tags=["players"])
except Exception:
    pass
