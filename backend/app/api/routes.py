from fastapi import APIRouter
from app.api import matches, health, auth, favorites
from app.api.hoy import router as hoy_router

router = APIRouter()

# Siempre vivos
router.include_router(health.router,    tags=["health"])

# Negocio
router.include_router(hoy_router,       prefix="/hoy",      tags=["hoy"])
router.include_router(matches.router,   prefix="/matches",   tags=["matches"])
router.include_router(auth.router,      prefix="/auth",      tags=["auth"])
router.include_router(favorites.router, prefix="/favorites", tags=["favorites"])

# Importaciones opcionales (no rompen si fallan)
try:
    from app.api import sports
    router.include_router(sports.router, prefix="/sports", tags=["sports"])
except Exception:
    pass

try:
    from app.api import players
    router.include_router(players.router, prefix="/players", tags=["players"])
except Exception:
    pass


try:
    from app.api import basketball
    router.include_router(basketball.router, prefix="/basketball", tags=["basketball"])
except Exception:
    pass


try:
    from app.api import football
    router.include_router(football.router, prefix="/football", tags=["football"])
except Exception:
    pass
