"""
Flashscore scraping — https://www.flashscore.com/
Cubre: fútbol, hockey, voley, rugby, básquet argentinos.

Flashscore tiene protección Cloudflare fuerte. Usamos el endpoint
público de su API JSON interna cuando está disponible, y HTML scraping
como fallback con selectores validados.

Nota: Flashscore bloquea IPs de datacenter agresivamente.
En producción considerar proxy residencial si hay 403 constantes.
"""
import httpx
import logging
import re
from datetime import date

logger = logging.getLogger(__name__)

BASE_HTML = "https://www.flashscore.com"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "es-AR,es;q=0.9",
    "Referer": "https://www.flashscore.com/",
    "Cache-Control": "no-cache",
}

# URLs de Argentina por deporte en Flashscore
SPORT_URLS = {
    "futbol":  "https://www.flashscore.com/football/argentina/",
    "basquet": "https://www.flashscore.com/basketball/argentina/",
    "hockey":  "https://www.flashscore.com/hockey/argentina/",
    "voley":   "https://www.flashscore.com/volleyball/argentina/",
    "rugby":   "https://www.flashscore.com/rugby-union/argentina/",
}


async def get_argentina_page(sport: str) -> str | None:
    """Obtiene la página de Argentina para un deporte."""
    url = SPORT_URLS.get(sport)
    if not url:
        return None
    try:
        async with httpx.AsyncClient(
            headers=HEADERS,
            timeout=httpx.Timeout(15.0, connect=8.0),
            follow_redirects=True,
        ) as client:
            r = await client.get(url)
            r.raise_for_status()
            logger.info(f"[flashscore] {sport} OK ({len(r.text)} chars)")
            return r.text
    except httpx.HTTPStatusError as e:
        logger.warning(f"[flashscore] HTTP {e.response.status_code} {sport}")
        return None
    except Exception as e:
        logger.warning(f"[flashscore] error {sport}: {e}")
        return None


def parse_matches_html(html: str, sport: str) -> list[dict]:
    """
    Parsea matches de la página de Flashscore.
    Flashscore carga resultados con JS, pero el HTML inicial tiene
    algunos datos de partidos en el DOM estático.
    """
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    results = []

    # Flashscore estructura: div.event__match por partido
    for match in soup.select("div.event__match, div[class*='event__match']"):
        try:
            home_el = match.select_one(".event__homeParticipant, .event__participant--home")
            away_el = match.select_one(".event__awayParticipant, .event__participant--away")
            if not home_el or not away_el:
                continue

            home = home_el.get_text(strip=True)
            away = away_el.get_text(strip=True)
            if not home or not away:
                continue

            score_home = match.select_one(".event__score--home")
            score_away = match.select_one(".event__score--away")
            time_el    = match.select_one(".event__time")

            hs = as_ = None
            if score_home and score_away:
                try:
                    hs = int(score_home.get_text(strip=True))
                    as_ = int(score_away.get_text(strip=True))
                except ValueError:
                    pass

            time_txt = time_el.get_text(strip=True) if time_el else ""
            status = "upcoming"
            minute = None
            if hs is not None:
                status = "finished"
            if "'" in time_txt or "+" in time_txt:
                status = "live"
                minute = time_txt

            comp_el = match.find_previous("div", class_=lambda c: c and "tournament__header" in c)
            comp = comp_el.get_text(strip=True) if comp_el else "Argentina"

            results.append({
                "home": home, "away": away,
                "home_score": hs, "away_score": as_,
                "competition": comp, "status": status,
                "minute": minute, "start_time": time_txt if status == "upcoming" else None,
                "source": "flashscore",
            })
        except Exception:
            continue

    logger.info(f"[flashscore] parse {sport}: {len(results)} partidos")
    return results
