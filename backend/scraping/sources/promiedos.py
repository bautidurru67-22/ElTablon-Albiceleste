"""
Promiedos.com.ar — fuente HTML para fútbol argentino local.
Selectores validados contra la estructura real del sitio.
"""
import httpx
import logging
import re
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

BASE = "https://www.promiedos.com.ar"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-AR,es;q=0.9",
    "Referer": "https://www.promiedos.com.ar/",
}

_STATUS_MAP = {
    "en juego": "live", "entretiempo": "live", "1t": "live", "2t": "live",
    "et": "live", "penales": "live", "pt": "live", "st": "live",
    "en el descanso": "live",
    "terminado": "finished", "finalizado": "finished", "final": "finished",
    "ft": "finished", "susp": "finished", "postergado": "finished",
    "cancelado": "finished",
}


async def get_today_html() -> str:
    async with httpx.AsyncClient(
        headers=HEADERS,
        timeout=httpx.Timeout(15.0, connect=8.0),
        follow_redirects=True,
    ) as client:
        r = await client.get(BASE)
        r.raise_for_status()
        logger.info(f"[promiedos] HTML {len(r.text)} chars")
        return r.text


def parse_matches(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    matches = []
    current_comp = "Liga Profesional Argentina"

    # Estructura Promiedos 2024:
    # div.fixcontainer > div.fixhead2 (nombre torneo) + div.fixrow (partido)
    for container in soup.select(
        "div.fixcontainer, div#main_center > div[class*='fix']"
    ):
        head = container.select_one(
            "div.fixhead2, div.fixhead, div.torneo, th.torneoth"
        )
        if head:
            t = head.get_text(strip=True)
            if t and len(t) > 1:
                current_comp = t

        for row in container.select("div.fixrow, tr.fixrow"):
            m = _parse_row(row, current_comp)
            if m:
                matches.append(m)

    # Fallback si no encontró nada
    if not matches:
        for row in soup.select("div[class*='fixrow'], tr[class*='partido']"):
            m = _parse_row(row, current_comp)
            if m:
                matches.append(m)

    logger.info(f"[promiedos] parse → {len(matches)} partidos")
    return matches


def _parse_row(row, competition: str) -> dict | None:
    try:
        home_tag = row.select_one(
            "div.eq1, div.equipo1, td.local, div[class*='home'], td[class*='eq1']"
        )
        away_tag = row.select_one(
            "div.eq2, div.equipo2, td.visitante, div[class*='away'], td[class*='eq2']"
        )
        if not home_tag or not away_tag:
            return None

        home = home_tag.get_text(strip=True)
        away = away_tag.get_text(strip=True)
        if not home or not away or home == away:
            return None

        score_tag  = row.select_one("div.resultado, div.score, td.score, div[class*='resultado']")
        time_tag   = row.select_one("div.hora, div.time, td.hora, div[class*='hora']")
        status_tag = row.select_one("div.estado, div.live, td.estado, div[class*='estado']")
        minute_tag = row.select_one("div.live, span.live, div[class*='minuto']")

        score_text  = (score_tag.get_text(strip=True)  if score_tag  else "")
        time_text   = (time_tag.get_text(strip=True)   if time_tag   else "")
        status_text = (status_tag.get_text(strip=True).lower() if status_tag else "")
        minute_text = (minute_tag.get_text(strip=True) if minute_tag else "")

        hs, as_, status, minute = _parse_score(
            score_text, time_text, status_text, minute_text
        )

        return {
            "competition": competition,
            "home": home, "away": away,
            "home_score": hs, "away_score": as_,
            "status": status, "minute": minute,
            "start_time": time_text if status == "upcoming" else None,
            "source": "promiedos",
        }
    except Exception:
        return None


def _parse_score(
    score_text: str, time_text: str, status_text: str, minute_text: str
) -> tuple:
    for key, val in _STATUS_MAP.items():
        if key in status_text or key in time_text.lower():
            nums = re.findall(r"\d+", score_text)
            hs = int(nums[0]) if len(nums) >= 2 else None
            as_ = int(nums[1]) if len(nums) >= 2 else None
            minute = minute_text or (time_text if val == "live" else None)
            return hs, as_, val, minute

    m = re.match(r"^(\d+)\s*[-:]\s*(\d+)$", score_text.strip())
    if m:
        return int(m.group(1)), int(m.group(2)), "finished", None

    if re.match(r"^\d{1,2}:\d{2}", time_text.strip()):
        return None, None, "upcoming", None

    return None, None, "upcoming", None
