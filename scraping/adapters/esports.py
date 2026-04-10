"""
Adapter de esports argentino.
Estado: preparado — sin scraping real activo.
Fuente objetivo: PandaScore API / Liquipedia (implementar en Fase 2).
Retorna vacío hasta activar.
"""
import logging
from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch

logger = logging.getLogger(__name__)

PANDASCORE_BASE = "https://api.pandascore.co"
LIQUIPEDIA_BASE = "https://liquipedia.net"


class EsportsAdapter(BaseScraper):
    async def scrape(self) -> list[NormalizedMatch]:
        logger.debug("[esports] STUB — activar con PandaScore API key en Fase 2")
        return []
