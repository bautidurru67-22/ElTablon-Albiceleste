from bs4 import BeautifulSoup
from scraping.base_scraper import BaseScraper


class LigaProfesionalScraper(BaseScraper):
    """
    Scraper para Liga Profesional Argentina.
    Fuente: promiedos.com.ar (estructura pública)
    """
    URL = "https://www.promiedos.com.ar"

    async def scrape(self) -> list[dict]:
        html = await self.fetch(self.URL)
        soup = BeautifulSoup(html, "lxml")
        matches = []

        # TODO: mapear selectores reales de Promiedos
        # Estructura esperada por partido:
        # {
        #   "competition": str,
        #   "home": str,
        #   "away": str,
        #   "home_score": int | None,
        #   "away_score": int | None,
        #   "status": "live" | "upcoming" | "finished",
        #   "minute": str | None,
        #   "time": str | None,
        # }

        return matches
