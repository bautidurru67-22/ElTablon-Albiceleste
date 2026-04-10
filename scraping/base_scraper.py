"""
BaseScraper — clase base para todos los scrapers del sistema.
Provee fetch HTML, fetch JSON, y retry automático.
"""
import httpx
from abc import ABC, abstractmethod
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from scraping.models import NormalizedMatch


class BaseScraper(ABC):

    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    # Subclases pueden sobreescribir
    EXTRA_HEADERS: dict = {}

    def __init__(self, timeout: int = 15):
        self.timeout = timeout

    def _get_headers(self) -> dict:
        return {**self.HEADERS, **self.EXTRA_HEADERS}

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
        reraise=True,
    )
    async def fetch_html(self, url: str) -> str:
        async with httpx.AsyncClient(
            headers=self._get_headers(), timeout=self.timeout, follow_redirects=True
        ) as client:
            r = await client.get(url)
            r.raise_for_status()
            return r.text

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.HTTPStatusError)),
        reraise=True,
    )
    async def fetch_json(self, url: str, extra_headers: dict | None = None) -> dict | list:
        headers = {**self._get_headers(), "Accept": "application/json"}
        if extra_headers:
            headers.update(extra_headers)
        async with httpx.AsyncClient(
            headers=headers, timeout=self.timeout, follow_redirects=True
        ) as client:
            r = await client.get(url)
            r.raise_for_status()
            return r.json()

    @abstractmethod
    async def scrape(self) -> list[NormalizedMatch]:
        """Ejecuta el scraping y devuelve lista de NormalizedMatch."""
        ...

    # Mantener compatibilidad con código anterior
    async def fetch(self, url: str) -> str:
        return await self.fetch_html(url)
