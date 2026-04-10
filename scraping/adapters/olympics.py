"""
Adapter de Juegos Olímpicos con deportistas argentinos.
Fuentes objetivo:
  - Olympics API oficial: olympics.com/en/api/
  - COA (Comité Olímpico Argentino): coa.org.ar
  - Sofascore (eventos olímpicos cuando están activos)
Cubrir:
  - Todos los deportes cuando hay JJOO (cada 4 años, 2028 LA)
  - Medallero histórico argentino
  - Atletas ARG clasificados / en competencia
  - Juegos Panamericanos / Sudamericanos (más frecuentes)
Estado: STUB — implementar antes de los JJOO 2028
Nota: fuera de ciclo olímpico, cubrir Panamericanos y clasificatorios.
"""
import logging
from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch

logger = logging.getLogger(__name__)

OLYMPICS_API = "https://olympics.com/en/api/v1"


class OlympicsAdapter(BaseScraper):
    async def scrape(self) -> list[NormalizedMatch]:
        # TODO: activar en períodos olímpicos
        # Verificar si hay JJOO, Panamericanos o clasificatorios activos
        logger.debug("[olympics] STUB — activar en ciclo olímpico")
        return []
