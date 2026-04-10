"""
Adapter de polo argentino.
Argentina domina el polo mundial — fuente primaria es la AAP.
Fuentes objetivo:
  - AAP (Asociación Argentina de Polo): aapolo.com
  - HPA (Hurlingham Polo Association)
  - USPA (US Polo Association)
Cubrir:
  - Abierto Argentino de Polo (Palermo — noviembre/diciembre)
  - Triple Corona Argentina (Tortugas, Hurlingham, Palermo)
  - Torneos internacionales con equipos ARG
  - Jugadores: Adolfo Cambiaso, Facundo Pieres, etc.
Estado: STUB — implementar en Fase 2
Nota: polo tiene calendario estacional (oct-dic para Palermo).
"""
import logging
from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch

logger = logging.getLogger(__name__)

AAP_BASE = "https://www.aapolo.com"


class PoloAdapter(BaseScraper):
    async def scrape(self) -> list[NormalizedMatch]:
        # TODO: implementar scraping de aapolo.com
        # Temporada Palermo: octubre-diciembre
        from datetime import date
        month = date.today().month
        if month not in range(9, 13):  # sep-dic
            logger.debug("[polo] fuera de temporada Palermo")
            # Igual puede haber torneos internacionales — stub retorna vacío por ahora
        logger.info("[polo] STUB — sin implementación activa")
        return []
