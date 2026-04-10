"""
Cliente para la API pública de la ATP Tour.
Endpoint oficial: https://www.atptour.com/en/scores/current
También usa el feed de resultados embebido en la página.
"""
import httpx
from datetime import date
from bs4 import BeautifulSoup

BASE_SCORES = "https://www.atptour.com/en/scores/current"
BASE_LIVE = "https://www.atptour.com/en/scores/current/live"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
    "Referer": "https://www.atptour.com/",
}


async def get_today_scores() -> str:
    """HTML de la página de scores del día."""
    async with httpx.AsyncClient(headers=HEADERS, timeout=15, follow_redirects=True) as client:
        r = await client.get(BASE_SCORES)
        r.raise_for_status()
        return r.text


async def get_live_scores() -> str:
    """HTML de la página de scores en vivo."""
    async with httpx.AsyncClient(headers=HEADERS, timeout=15, follow_redirects=True) as client:
        r = await client.get(BASE_LIVE)
        r.raise_for_status()
        return r.text


def parse_match_row(row_tag) -> dict | None:
    """
    Parsea una fila de partido del HTML de ATP.
    Retorna dict crudo o None si no es parseable.
    """
    try:
        cells = row_tag.find_all("td")
        if len(cells) < 4:
            return None

        player1 = cells[0].get_text(strip=True)
        player2 = cells[1].get_text(strip=True)
        score_raw = cells[2].get_text(strip=True) if len(cells) > 2 else ""
        status_text = cells[-1].get_text(strip=True).lower()

        status = "finished"
        if "live" in status_text or "in progress" in status_text:
            status = "live"
        elif "vs" in score_raw or not score_raw:
            status = "upcoming"

        return {
            "player1": player1,
            "player2": player2,
            "score_raw": score_raw,
            "status": status,
        }
    except Exception:
        return None
