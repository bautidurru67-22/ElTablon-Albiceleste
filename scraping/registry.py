"""
Registry central de adapters.
ADAPTER_REGISTRY es el único lugar donde se registran los adapters activos.
El orchestrator y el runner lo consumen — nunca importan adapters directamente.
"""
from scraping.base_scraper import BaseScraper

# --- Implementados (reales) ---
from scraping.adapters.football   import FootballAdapter
from scraping.adapters.tennis     import TennisAdapter
from scraping.adapters.basketball import BasketballAdapter
from scraping.adapters.rugby      import RugbyAdapter
from scraping.adapters.hockey     import HockeyAdapter

# --- Stubs (Sofascore fallback o vacíos) ---
from scraping.adapters.volleyball import VolleyballAdapter
from scraping.adapters.handball   import HandballAdapter
from scraping.adapters.futsal     import FutsalAdapter
from scraping.adapters.motorsport import MotorsportAdapter
from scraping.adapters.motogp     import MotoGPAdapter
from scraping.adapters.dakar      import DakarAdapter
from scraping.adapters.golf       import GolfAdapter
from scraping.adapters.boxing     import BoxingAdapter
from scraping.adapters.polo       import PoloAdapter
from scraping.adapters.olympics   import OlympicsAdapter
from scraping.adapters.esports    import EsportsAdapter

ADAPTER_REGISTRY: dict[str, type[BaseScraper]] = {
    # Implementados
    "futbol":      FootballAdapter,
    "tenis":       TennisAdapter,
    "basquet":     BasketballAdapter,
    "rugby":       RugbyAdapter,
    "hockey":      HockeyAdapter,
    # Stubs funcionales (Sofascore fallback)
    "voley":       VolleyballAdapter,
    "handball":    HandballAdapter,
    "futsal":      FutsalAdapter,
    "motorsport":  MotorsportAdapter,
    "motogp":      MotoGPAdapter,
    "boxeo":       BoxingAdapter,
    "golf":        GolfAdapter,
    "esports":     EsportsAdapter,
    # Stubs estacionales (retornan vacío fuera de temporada)
    "polo":        PoloAdapter,
    "dakar":       DakarAdapter,
    "olimpicos":   OlympicsAdapter,
}


# ---------------------------------------------------------------------------
# Helpers de conveniencia (compatibilidad con código anterior)
# ---------------------------------------------------------------------------

async def run_scraper(sport: str) -> list[dict]:
    """Ejecuta un deporte y retorna lista de backend dicts."""
    from scraping.orchestrator.runner import run
    return await run(sports=[sport], only_argentina=True)


async def run_all() -> dict[str, list[dict]]:
    """Ejecuta todos y retorna dict {sport: [backend_dicts]}."""
    from scraping.orchestrator.coordinator import ScrapingCoordinator
    coordinator = ScrapingCoordinator(ADAPTER_REGISTRY)
    all_results = await coordinator.run_all()
    return {
        sport: [m.to_backend_dict() for m in matches]
        for sport, matches in all_results.items()
    }
