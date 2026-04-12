"""
AFA (Asociación del Fútbol Argentino) — fuente oficial Argentina.
https://www.afa.com.ar/

AFA no tiene API pública, scraping HTML del calendario.
También cubre futsal vía afa.com.ar/inferiores/futsal
"""
import httpx
import logging
import re
from datetime import date

logger = logging.getLogger(__name__)

BASE = "https://www.afa.com.ar"
FIXTURES_URL = f"{BASE}/primera-division/fixture"
FUTSAL_URL   = f"{BASE}/futsal"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-AR,es;q=0.9",
    "Referer": "https://www.afa.com.ar/",
}


async def get_fixture_html(url: str = FIXTURES_URL) -> str | None:
    try:
        async with httpx.AsyncClient(
            headers=HEADERS,
            timeout=httpx.Timeout(15.0, connect=8.0),
            follow_redirects=True,
        ) as client:
            r = await client.get(url)
            r.raise_for_status()
            logger.info(f"[afa] HTML OK {url} ({len(r.text)} chars)")
            return r.text
    except httpx.HTTPStatusError as e:
        logger.warning(f"[afa] HTTP {e.response.status_code}: {url}")
        return None
    except Exception as e:
        logger.warning(f"[afa] error: {e}")
        return None


def parse_fixture(html: str, competition: str = "Liga Profesional Argentina") -> list[dict]:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    results = []
    today = date.today().strftime("%d/%m/%Y")

    for match in soup.select(
        "div.partido, div.match, article.match, div[class*='fixture'], div[class*='partido']"
    ):
        try:
            home_el = match.select_one(".local, .home, .team-home, .equipo-local, [class*='local']")
            away_el = match.select_one(".visitante, .away, .team-away, .equipo-visitante, [class*='visitante']")
            if not home_el or not away_el:
                continue

            home = home_el.get_text(strip=True)
            away = away_el.get_text(strip=True)
            if not home or not away or home == away:
                continue

            date_el  = match.select_one(".fecha, .date, [class*='fecha']")
            time_el  = match.select_one(".hora, .time, [class*='hora']")
            score_el = match.select_one(".score, .resultado, [class*='score'], [class*='resultado']")

            date_txt = date_el.get_text(strip=True) if date_el else ""
            time_txt = time_el.get_text(strip=True) if time_el else ""

            if date_txt and today not in date_txt:
                continue

            hs = as_ = None
            score_txt = score_el.get_text(strip=True) if score_el else ""
            m = re.match(r"^(\d+)\s*[-:]\s*(\d+)$", score_txt.strip())
            if m:
                hs, as_ = int(m.group(1)), int(m.group(2))

            status = "finished" if hs is not None else "upcoming"

            results.append({
                "home": home, "away": away,
                "home_score": hs, "away_score": as_,
                "competition": competition,
                "status": status, "minute": None,
                "start_time": time_txt if status == "upcoming" else None,
                "source": "afa",
            })
        except Exception:
            continue

    logger.info(f"[afa] parse_fixture → {len(results)} partidos hoy")
    return results
