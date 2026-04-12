"""Adapter golf — Sofascore primary."""
import logging
from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch
from scraping.sources import sofascore
from scraping.normalizers import sofascore_normalizer

logger = logging.getLogger(__name__)

class GolfAdapter(BaseScraper):
    async def scrape(self) -> list[NormalizedMatch]:
        matches = []
        try:
            data = await sofascore.get_events_by_date("golf")
            events = data.get("events", [])
            ss = sofascore_normalizer.normalize_events(events, "golf")
            logger.info(f"[golf/sofascore] {len(ss)} con ARG")
            matches.extend(ss)
        except Exception as e:
            logger.warning(f"[golf/sofascore] falló: {e}")
        logger.info(f"[golf] TOTAL: {len(matches)}")
        return matches
