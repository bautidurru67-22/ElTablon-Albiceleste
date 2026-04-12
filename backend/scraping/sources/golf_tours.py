"""
Cliente para leaderboards de golf.
- DP World Tour (European Tour): dpwtour.com tiene JSON embebido
- PGA Tour stats API: pgatour.com/stats
Ambas son scrapeables sin autenticación para datos públicos.
"""
import httpx
from bs4 import BeautifulSoup

DPWT_BASE    = "https://www.dpwtour.com"
DPWT_SCORES  = f"{DPWT_BASE}/en/tournament/current/leaderboard"

PGA_BASE     = "https://www.pgatour.com"
PGA_SCORES   = f"{PGA_BASE}/leaderboard"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

# Jugadores argentinos a buscar en leaderboards
ARG_GOLF_PLAYERS = {
    "grillo", "emiliano grillo",
    "gomez", "fabian gomez", "fabián gómez",
    "cabrera", "angel cabrera", "ángel cabrera",
}


async def get_dpwt_leaderboard_html() -> str:
    async with httpx.AsyncClient(headers=HEADERS, timeout=15, follow_redirects=True) as client:
        r = await client.get(DPWT_SCORES)
        r.raise_for_status()
        return r.text


async def get_pga_leaderboard_html() -> str:
    async with httpx.AsyncClient(headers=HEADERS, timeout=15, follow_redirects=True) as client:
        r = await client.get(PGA_SCORES)
        r.raise_for_status()
        return r.text


def parse_leaderboard(html: str, source: str) -> list[dict]:
    """
    Parsea leaderboard de golf buscando jugadores argentinos.
    Retorna lista de dicts representando la posición del jugador ARG.
    Formato de salida: match-like para compatibilidad con el normalizer.
    """
    soup = BeautifulSoup(html, "lxml")
    results = []

    # Selectores genéricos — ajustar por sitio en producción
    for row in soup.select("tr.player-row, div.leaderboard-row, li.player"):
        try:
            name_tag = row.select_one(".player-name, .name, td.player")
            if not name_tag:
                continue
            name = name_tag.get_text(strip=True).lower()

            if not any(arg in name for arg in ARG_GOLF_PLAYERS):
                continue

            position_tag = row.select_one(".position, .pos, td.rank")
            score_tag    = row.select_one(".score, .total, td.score")
            tournament_tag = row.find_previous(
                ["div", "h1", "h2"], class_=["tournament-name", "event-name"]
            )

            results.append({
                "player": name_tag.get_text(strip=True),
                "position": position_tag.get_text(strip=True) if position_tag else "?",
                "score": score_tag.get_text(strip=True) if score_tag else "",
                "tournament": tournament_tag.get_text(strip=True) if tournament_tag else "Golf Tournament",
                "source": source,
            })
        except Exception:
            continue

    return results
