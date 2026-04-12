from bs4 import BeautifulSoup
from scraping.base_scraper import BaseScraper

ARGENTINOS_ATP = [
    "cerundolo", "etcheverry", "baez", "navone",
    "delbonis", "zeballos", "granollers",
]


class TenisScraper(BaseScraper):
    """
    Scraper para tenis argentino.
    Filtra resultados ATP/WTA/Challenger donde juegue un argentino.
    Fuente: flashscore / livescore (a definir)
    """

    async def scrape(self) -> list[dict]:
        # TODO: implementar scraping real
        # Lógica: obtener todos los partidos del día → filtrar por jugador argentino
        return []
