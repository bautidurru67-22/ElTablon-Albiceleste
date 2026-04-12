"""Adapter olímpicos — stub hasta 2028."""
import logging
from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch

logger = logging.getLogger(__name__)

class OlympicsAdapter(BaseScraper):
    async def scrape(self) -> list[NormalizedMatch]:
        logger.debug("[olympics] stub — activar en ciclo olímpico 2028")
        return []
