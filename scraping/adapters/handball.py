"""Adapter handball — Sofascore primary."""
import logging
from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch
from scraping.sources import sofascore
from scraping.normalizers import sofascore_normalizer

logger = logging.getLogger(__name__)

class HandballAdapter(BaseScraper):
    async def scrape(self) -> list[NormalizedMatch]:
        matches = []
        for fn, label in [
            (lambda: sofascore.get_events_by_date("handball"), "scheduled"),
            (lambda: sofascore.get_live_events("handball"), "live"),
        ]:
            try:
                data = await fn()
                events = data.get("events", [])
                ss = sofascore_normalizer.normalize_events(events, "handball")
                existing = {m.id for m in matches}
                new = [m for m in ss if m.id not in existing]
                logger.info(f"[handball/sofascore-{label}] {len(new)} con ARG")
                matches.extend(new)
            except Exception as e:
                logger.warning(f"[handball/sofascore-{label}] falló: {e}")
        logger.info(f"[handball] TOTAL: {len(matches)}")
        return matches
