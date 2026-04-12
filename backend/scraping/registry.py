"""
Registry central de adapters.
Safe imports: un adapter roto no rompe todo el sistema.
"""
import logging
import importlib
from scraping.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


def _load(module: str, cls: str):
    try:
        return getattr(importlib.import_module(module), cls)
    except Exception as e:
        logger.error(f"[registry] no se pudo cargar {cls} desde {module}: {e}")
        return None


_MAP = {
    "futbol":     ("scraping.adapters.football",   "FootballAdapter"),
    "tenis":      ("scraping.adapters.tennis",     "TennisAdapter"),
    "basquet":    ("scraping.adapters.basketball", "BasketballAdapter"),
    "rugby":      ("scraping.adapters.rugby",      "RugbyAdapter"),
    "hockey":     ("scraping.adapters.hockey",     "HockeyAdapter"),
    "voley":      ("scraping.adapters.volleyball", "VolleyballAdapter"),
    "handball":   ("scraping.adapters.handball",   "HandballAdapter"),
    "futsal":     ("scraping.adapters.futsal",     "FutsalAdapter"),
    "motorsport": ("scraping.adapters.motorsport", "MotorsportAdapter"),
    "motogp":     ("scraping.adapters.motogp",     "MotoGPAdapter"),
    "boxeo":      ("scraping.adapters.boxing",     "BoxingAdapter"),
    "golf":       ("scraping.adapters.golf",       "GolfAdapter"),
    "esports":    ("scraping.adapters.esports",    "EsportsAdapter"),
    "polo":       ("scraping.adapters.polo",       "PoloAdapter"),
    "dakar":      ("scraping.adapters.dakar",      "DakarAdapter"),
    "olimpicos":  ("scraping.adapters.olympics",   "OlympicsAdapter"),
}

ADAPTER_REGISTRY: dict[str, type[BaseScraper]] = {}

for sport, (mod, cls_name) in _MAP.items():
    cls = _load(mod, cls_name)
    if cls is not None:
        ADAPTER_REGISTRY[sport] = cls

logger.info(f"[registry] activos: {list(ADAPTER_REGISTRY.keys())}")
