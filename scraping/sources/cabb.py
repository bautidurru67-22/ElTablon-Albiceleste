"""
CABB (Confederación Argentina de Básquetbol) — fuente oficial básquet.
https://cabb.com.ar/

También: LNB (lnb.com.ar), Latinbasket (latinbasket.com)
"""
import httpx
import logging
import re
from datetime import date

logger = logging.getLogger(__name__)

CABB_FIXTURES = "https://cabb.com.ar/competencias"
LNB_PARTIDOS  = "https://www.lnb.com.ar/partidos"
LATINBASKET   = "https://www.latinbasket.com/Argentina/basketball-Argentina.asp"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-AR,es;q=0.9",
}


async def get_lnb_html() -> str | None:
    try:
        async with httpx.AsyncClient(
            headers={**HEADERS, "Referer": "https://www.lnb.com.ar/"},
            timeout=httpx.Timeout(12.0),
            follow_redirects=True,
        ) as client:
            r = await client.get(LNB_PARTIDOS)
            r.raise_for_status()
            logger.info(f"[cabb/lnb] HTML OK {len(r.text)} chars")
            return r.text
    except Exception as e:
        logger.warning(f"[cabb/lnb] error: {e}")
        return None


async def get_cabb_html() -> str | None:
    try:
        async with httpx.AsyncClient(
            headers={**HEADERS, "Referer": "https://cabb.com.ar/"},
            timeout=httpx.Timeout(12.0),
            follow_redirects=True,
        ) as client:
            r = await client.get(CABB_FIXTURES)
            r.raise_for_status()
            logger.info(f"[cabb] HTML OK {len(r.text)} chars")
            return r.text
    except Exception as e:
        logger.warning(f"[cabb] error: {e}")
        return None


def parse_lnb(html: str) -> list[dict]:
    """Parsea la página de LNB."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "lxml")
    results = []
    competition = "Liga Nacional de Básquet"

    for row in soup.select(
        "div.partido, article.match, tr[class*='match'], div[class*='fixture'], "
        "div[class*='game'], table.games tr"
    ):
        try:
            home_el = row.select_one(
                ".local, .home, .equipo-local, .team-a, td.home, [class*='equipo1']"
            )
            away_el = row.select_one(
                ".visitante, .away, .equipo-visitante, .team-b, td.away, [class*='equipo2']"
            )
            if not home_el or not away_el:
                continue
            home = home_el.get_text(strip=True)
            away = away_el.get_text(strip=True)
            if not home or not away:
                continue

            score_el = row.select_one(".score, .resultado, .marcador, [class*='score']")
            time_el  = row.select_one(".hora, .time, .horario, [class*='hora']")

            hs = as_ = None
            if score_el:
                parts = re.findall(r"\d+", score_el.get_text())
                if len(parts) >= 2:
                    hs, as_ = int(parts[0]), int(parts[1])

            status = "finished" if hs is not None else "upcoming"
            time_txt = time_el.get_text(strip=True) if time_el else None

            results.append({
                "home": home, "away": away,
                "home_score": hs, "away_score": as_,
                "competition": competition, "status": status,
                "minute": None, "start_time": time_txt,
                "source": "lnb",
            })
        except Exception:
            continue

    logger.info(f"[cabb/lnb] parse → {len(results)}")
    return results
