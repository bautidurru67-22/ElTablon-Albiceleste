"""
Adapter para el Rally Dakar y rallies off-road con pilotos argentinos.
Fuentes objetivo:
  - Dakar oficial: dakar.com/en/results
  - Sofascore no cubre Dakar bien — usar fuente directa
  - dakar.com tiene API/JSON embebida en la página
Cubrir:
  - Etapas y clasificación general del Dakar
  - Pilotos y equipos argentinos (autos, motos, camiones, quads)
  - Rally Argentino / Rally de Córdoba
Nota: el Dakar es evento anual (enero). Fuera de temporada retornar vacío.
Estado: STUB — implementar en Fase 2
"""
import logging
from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch

logger = logging.getLogger(__name__)

DAKAR_BASE = "https://www.dakar.com/en"


class DakarAdapter(BaseScraper):
    async def scrape(self) -> list[NormalizedMatch]:
        # Dakar ocurre en enero — fuera de temporada retorna vacío sin error
        from datetime import date
        if date.today().month != 1:
            logger.debug("[dakar] fuera de temporada — sin eventos")
            return []
        # TODO: implementar scraping de etapas y clasificación en enero
        logger.info("[dakar] STUB — implementar scraping en temporada")
        return []
