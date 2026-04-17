import asyncio
import logging
from scraping.orchestrator.runner import run

logger = logging.getLogger(__name__)

async def start_scraping_loop():
    while True:
        try:
            logger.info("[SCRAPER] Ejecutando scraping completo...")
            await run()
            logger.info("[SCRAPER] OK")
        except Exception as e:
            logger.error(f"[SCRAPER] ERROR: {e}")

        # cada 60 segundos (después ajustamos)
        await asyncio.sleep(60)
