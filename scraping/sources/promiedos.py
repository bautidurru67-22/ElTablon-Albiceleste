"""
Cliente para Promiedos — principal fuente de fútbol argentino.
URL: https://www.promiedos.com.ar
Parsea la tabla de partidos del día desde el HTML.
"""
import httpx
from bs4 import BeautifulSoup

BASE = "https://www.promiedos.com.ar"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept-Language": "es-AR,es;q=0.9",
    "Referer": "https://www.promiedos.com.ar/",
}

# Mapeo de texto de estado Promiedos → status normalizado
STATUS_MAP: dict[str, str] = {
    "en juego": "live",
    "entretiempo": "live",
    "1t": "live",
    "2t": "live",
    "terminado": "finished",
    "finalizado": "finished",
    "susp": "finished",
}


async def get_today_html() -> str:
    async with httpx.AsyncClient(headers=HEADERS, timeout=15, follow_redirects=True) as client:
        r = await client.get(BASE)
        r.raise_for_status()
        return r.text


def parse_matches(html: str) -> list[dict]:
    """
    Parsea partidos del HTML de Promiedos.
    Retorna lista de dicts crudos con estructura:
    {
        competition, home, away,
        home_score, away_score,
        status, minute, start_time
    }
    """
    soup = BeautifulSoup(html, "lxml")
    matches = []

    # Promiedos usa tabla con class "fixres" o similar
    # Selector real a ajustar inspeccionando el DOM en producción
    current_competition = "Liga Profesional Argentina"

    for row in soup.select("div.fixture, tr.partido, div.partido"):
        try:
            # Intentar extraer competition header si existe en el bloque previo
            comp_tag = row.find_previous("div.torneo, td.torneo, span.torneo")
            if comp_tag:
                current_competition = comp_tag.get_text(strip=True)

            home_tag = row.select_one(".home, .local, .eq1")
            away_tag = row.select_one(".away, .visitante, .eq2")
            score_tag = row.select_one(".score, .resultado, .goles")
            time_tag = row.select_one(".time, .hora, .minuto")

            if not home_tag or not away_tag:
                continue

            home = home_tag.get_text(strip=True)
            away = away_tag.get_text(strip=True)
            score_text = score_tag.get_text(strip=True) if score_tag else ""
            time_text = time_tag.get_text(strip=True) if time_tag else ""

            home_score, away_score, status, minute = _parse_score(score_text, time_text)

            matches.append({
                "competition": current_competition,
                "home": home,
                "away": away,
                "home_score": home_score,
                "away_score": away_score,
                "status": status,
                "minute": minute,
                "start_time": time_text if status == "upcoming" else None,
            })
        except Exception:
            continue

    return matches


def _parse_score(score_text: str, time_text: str) -> tuple:
    """Retorna (home_score, away_score, status, minute)."""
    score_text = score_text.strip()
    time_lower = time_text.lower().strip()

    # Buscar status por texto de tiempo
    for key, val in STATUS_MAP.items():
        if key in time_lower:
            # Está en vivo o terminado
            parts = score_text.replace("-", " ").split()
            if len(parts) == 2:
                try:
                    return int(parts[0]), int(parts[1]), val, time_text
                except ValueError:
                    pass
            return None, None, val, time_text

    # Si hay ":" es hora de inicio → upcoming
    if ":" in time_text and not score_text:
        return None, None, "upcoming", None

    # Intentar parsear score como "X-Y"
    if "-" in score_text:
        parts = score_text.split("-")
        if len(parts) == 2:
            try:
                return int(parts[0].strip()), int(parts[1].strip()), "finished", None
            except ValueError:
                pass

    return None, None, "upcoming", None
