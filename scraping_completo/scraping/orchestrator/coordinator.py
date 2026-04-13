"""
Coordinator — ejecuta adapters en paralelo, deduplica, loggea.
"""
import asyncio
import logging
from scraping.models import NormalizedMatch
from scraping.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class ScrapingCoordinator:

    def __init__(
        self,
        adapters: dict[str, type[BaseScraper]],
        timeout_per_adapter: int = 30,
    ):
        self.adapters = adapters
        self.timeout  = timeout_per_adapter

    async def run_one(self, sport: str) -> list[NormalizedMatch]:
        cls = self.adapters.get(sport)
        if not cls:
            return []
        try:
            adapter = cls()
            results = await asyncio.wait_for(adapter.scrape(), timeout=self.timeout)
            logger.info(f"[coord] {sport:12s} → {len(results):3d} partidos")
            return results or []
        except asyncio.TimeoutError:
            logger.error(f"[coord] TIMEOUT {sport} ({self.timeout}s)")
            return []
        except Exception as e:
            logger.error(f"[coord] ERROR {sport}: {e}", exc_info=True)
            return []

    async def run_all(self) -> dict[str, list[NormalizedMatch]]:
        logger.info(f"[coord] run_all deportes={list(self.adapters.keys())}")
        tasks = {
            sport: asyncio.create_task(self.run_one(sport))
            for sport in self.adapters
        }
        results = {}
        for sport, task in tasks.items():
            results[sport] = await task
        total = sum(len(v) for v in results.values())
        summary = " | ".join(f"{s}={len(v)}" for s, v in results.items() if v)
        logger.info(f"[coord] run_all done | {summary} | TOTAL={total}")
        return results

    async def run_all_flat(self) -> list[NormalizedMatch]:
        all_results = await self.run_all()
        seen: set[str] = set()
        flat: list[NormalizedMatch] = []
        for matches in all_results.values():
            for m in matches:
                if m.id not in seen:
                    seen.add(m.id)
                    flat.append(m)
        STATUS_ORDER = {"live": 0, "upcoming": 1, "finished": 2}
        flat.sort(key=lambda m: (STATUS_ORDER.get(m.status, 9), m.start_time_arg or ""))
        by_sport: dict[str, int] = {}
        for m in flat:
            by_sport[m.sport] = by_sport.get(m.sport, 0) + 1
        logger.info(
            f"[coord] flat {len(flat)} únicos | "
            + " ".join(f"{s}={n}" for s, n in by_sport.items())
        )
        return flat

    def get_argentina_matches(self, matches: list[NormalizedMatch]) -> list[NormalizedMatch]:
        arg = [m for m in matches if m.argentina_relevance != "none"]
        disc = len(matches) - len(arg)
        logger.info(f"[coord] ARG filter: {len(arg)} pasan, {disc} descartados")
        return arg
