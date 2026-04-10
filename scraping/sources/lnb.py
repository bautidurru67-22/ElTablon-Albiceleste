"""
Cliente para lnb.com.ar — Liga Nacional de Básquet Argentina.
Parsea resultados y fixtures del día desde el HTML público.
"""
import httpx
from bs4 import BeautifulSoup

BASE = "https://www.lnb.com.ar"
FIXTURES_URL = f"{BASE}/partidos"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "es-AR,es;q=0.9",
    "Referer": BASE,
}

STATUS_MAP = {
    "en curso": "live",
    "en juego": "live",
    "live": "live",
    "finalizado": "finished",
    "final": "finished",
    "suspendido": "finished",
}


async def get_today_html() -> str:
    async with httpx.AsyncClient(headers=HEADERS, timeout=15, follow_redirects=True) as client:
        r = await client.get(FIXTURES_URL)
        r.raise_for_status()
        return r.text


def parse_matches(html: str) -> list[dict]:
    """
    Parsea partidos del HTML de lnb.com.ar.
    Retorna lista de dicts crudos normalizables.
    Selectores a validar contra DOM real en producción.
    """
    soup = BeautifulSoup(html, "lxml")
    matches = []
    current_competition = "Liga Nacional de Básquet"

    for row in soup.select(
        "div.partido, article.match, div.fixture, li.game-item, tr.partido-row"
    ):
        try:
            comp_tag = row.find_previous(
                ["div", "h2", "h3"], class_=["competencia", "torneo", "league-name"]
            )
            if comp_tag:
                current_competition = comp_tag.get_text(strip=True)

            home_tag = row.select_one(".local, .home, .equipo-local, .team-home")
            away_tag = row.select_one(".visitante, .away, .equipo-visitante, .team-away")
            if not home_tag or not away_tag:
                continue

            home = home_tag.get_text(strip=True)
            away = away_tag.get_text(strip=True)
            if not home or not away:
                continue

            score_tag = row.select_one(".resultado, .score, .marcador")
            time_tag  = row.select_one(".hora, .time, .horario")
            status_tag = row.select_one(".estado, .status, .estado-partido")

            score_text  = score_tag.get_text(strip=True) if score_tag else ""
            time_text   = time_tag.get_text(strip=True) if time_tag else ""
            status_text = status_tag.get_text(strip=True).lower() if status_tag else ""

            home_score = away_score = None
            if "-" in score_text:
                parts = score_text.split("-")
                if len(parts) == 2:
                    try:
                        home_score = int(parts[0].strip())
                        away_score = int(parts[1].strip())
                    except ValueError:
                        pass

            status = STATUS_MAP.get(status_text, "upcoming")
            if home_score is not None and status == "upcoming":
                status = "finished"

            matches.append({
                "competition": current_competition,
                "home": home,
                "away": away,
                "home_score": home_score,
                "away_score": away_score,
                "status": status,
                "start_time": time_text if status == "upcoming" else None,
                "source": "lnb",
            })
        except Exception:
            continue

    return matches
