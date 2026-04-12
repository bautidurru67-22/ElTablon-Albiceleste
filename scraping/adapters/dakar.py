"""Adapter Dakar — solo en enero."""
import logging
from datetime import date
from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch

logger = logging.getLogger(__name__)

class DakarAdapter(BaseScraper):
    async def scrape(self) -> list[NormalizedMatch]:
        if date.today().month != 1:
            logger.debug("[dakar] fuera de temporada (solo enero)")
            return []
        logger.info("[dakar] temporada activa — scraping pendiente de implementar")
        return []
