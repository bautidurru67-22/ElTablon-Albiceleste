"""Adapter esports — Sofascore."""
import logging
from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch
from scraping.sources import sofascore
from scraping.normalizers import sofascore_normalizer

logger = logging.getLogger(__name__)

class EsportsAdapter(BaseScraper):
    async def scrape(self) -> list[NormalizedMatch]:
        matches = []
        try:
            data = await sofascore.get_events_by_date("esports")
            events = data.get("events", [])
            ss = sofascore_normalizer.normalize_events(events, "esports")
            logger.info(f"[esports/sofascore] {len(ss)} con ARG")
            matches.extend(ss)
        except Exception as e:
            logger.warning(f"[esports/sofascore] falló: {e}")
        logger.info(f"[esports] TOTAL: {len(matches)}")
        return matches
