"""Futsal — Sofascore (única fuente viable)."""
import logging
from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch
from scraping.sources.sofascore_safe import get_events_by_date as ss_today, get_live_events as ss_live
from scraping.normalizers import sofascore_normalizer
logger = logging.getLogger(__name__)

class FutsalAdapter(BaseScraper):
    async def scrape(self):
        matches, seen = [], set()
        try:
            for fn in [ss_today, ss_live]:
                data = await fn("futsal")
                for m in sofascore_normalizer.normalize_events(data.get("events",[]), "futsal"):
                    if m.id not in seen: seen.add(m.id); matches.append(m)
            logger.info(f"[futsal/sofascore] {len(matches)}")
        except Exception as e: logger.warning(f"[futsal/sofascore] {e}")
        logger.info(f"[futsal] TOTAL {len(matches)}"); return matches
