"""
Adapter de fútbol argentino.
Fuente primaria: Promiedos (HTML scraping)
Fallback: Sofascore API (filtrando partidos con argentina_relevance)
"""
import logging
from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch
from scraping.sources import promiedos, sofascore
from scraping.normalizers import promiedos_normalizer, sofascore_normalizer

logger = logging.getLogger(__name__)


class FootballAdapter(BaseScraper):
    """
    Fútbol argentino: Liga Profesional, Copa Argentina, Libertadores, Sudamericana.
    También detecta jugadores argentinos en ligas del exterior.
    """
    EXTRA_HEADERS = {"Referer": "https://www.promiedos.com.ar/"}

    async def scrape(self) -> list[NormalizedMatch]:
        matches: list[NormalizedMatch] = []

        # --- Fuente 1: Promiedos (fútbol argentino local) ---
        try:
            html = await promiedos.get_today_html()
            raws = promiedos.parse_matches(html)
            local = promiedos_normalizer.normalize_matches(raws)
            logger.info(f"[football/promiedos] {len(local)} partidos encontrados")
            matches.extend(local)
        except Exception as e:
            logger.warning(f"[football/promiedos] falló: {e}")

        # --- Fuente 2: Sofascore (fútbol internacional con ARG) ---
        try:
            data = await sofascore.get_events_by_date("futbol")
            events = data.get("events", [])
            intl = sofascore_normalizer.normalize_events(events, "futbol")
            # Evitar duplicados por id
            existing_ids = {m.id for m in matches}
            new = [m for m in intl if m.id not in existing_ids]
            logger.info(f"[football/sofascore] {len(new)} partidos adicionales con ARG")
            matches.extend(new)
        except Exception as e:
            logger.warning(f"[football/sofascore] falló: {e}")

        # Fuente 3: En vivo de Sofascore
        try:
            data = await sofascore.get_live_events("futbol")
            events = data.get("events", [])
            live = sofascore_normalizer.normalize_events(events, "futbol")
            existing_ids = {m.id for m in matches}
            new_live = [m for m in live if m.id not in existing_ids]
            logger.info(f"[football/sofascore-live] {len(new_live)} en vivo nuevos")
            matches.extend(new_live)
        except Exception as e:
            logger.warning(f"[football/sofascore-live] falló: {e}")

        return matches
