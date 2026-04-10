"""
Coordinator — gestiona la ejecución de adapters y la deduplicación de resultados.
No sabe nada de HTTP ni de scrapers específicos: solo coordina.
"""
import asyncio
import logging
from scraping.models import NormalizedMatch
from scraping.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class ScrapingCoordinator:
    """
    Recibe un dict {sport: AdapterClass} y los ejecuta
    con control de errores, timeout por adapter, y deduplicación global.
    """

    def __init__(
        self,
        adapters: dict[str, type[BaseScraper]],
        timeout_per_adapter: int = 30,
    ):
        self.adapters = adapters
        self.timeout = timeout_per_adapter

    async def run_one(self, sport: str) -> list[NormalizedMatch]:
        """Ejecuta un único adapter con timeout y manejo de errores."""
        cls = self.adapters.get(sport)
        if not cls:
            logger.warning(f"[coordinator] no hay adapter para '{sport}'")
            return []
        try:
            adapter = cls()
            results = await asyncio.wait_for(adapter.scrape(), timeout=self.timeout)
            logger.info(f"[coordinator] {sport} → {len(results)} partidos")
            return results
        except asyncio.TimeoutError:
            logger.error(f"[coordinator] timeout en '{sport}' ({self.timeout}s)")
            return []
        except Exception as e:
            logger.error(f"[coordinator] error en '{sport}': {e}")
            return []

    async def run_all(self) -> dict[str, list[NormalizedMatch]]:
        """Ejecuta todos los adapters en paralelo."""
        tasks = {
            sport: asyncio.create_task(self.run_one(sport))
            for sport in self.adapters
        }
        results: dict[str, list[NormalizedMatch]] = {}
        for sport, task in tasks.items():
            results[sport] = await task
        return results

    async def run_all_flat(self) -> list[NormalizedMatch]:
        """
        Ejecuta todos los adapters y retorna lista única deduplicada por id.
        Orden: live primero, luego upcoming, luego finished.
        """
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
        return flat

    def get_argentina_matches(
        self, matches: list[NormalizedMatch]
    ) -> list[NormalizedMatch]:
        """Filtra solo partidos con relevancia argentina."""
        return [m for m in matches if m.argentina_relevance != "none"]
