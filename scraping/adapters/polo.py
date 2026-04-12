"""Adapter polo — temporada oct-dic."""
import logging
from datetime import date
from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch
from scraping.sources import sofascore
from scraping.normalizers import sofascore_normalizer

logger = logging.getLogger(__name__)

class PoloAdapter(BaseScraper):
    async def scrape(self) -> list[NormalizedMatch]:
        matches = []
        try:
            data = await sofascore.get_events_by_date("polo")
            events = data.get("events", [])
            ss = sofascore_normalizer.normalize_events(events, "polo")
            logger.info(f"[polo/sofascore] {len(ss)} con ARG")
            matches.extend(ss)
        except Exception as e:
            logger.warning(f"[polo/sofascore] falló: {e}")
        logger.info(f"[polo] TOTAL: {len(matches)}")
        return matches
