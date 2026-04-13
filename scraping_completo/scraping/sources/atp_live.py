"""
ATP Tour Live Scores — endpoint JSON no oficial pero estable.
Usado por la web oficial de ATP para cargar partidos.
No requiere auth. Retorna partidos del día filtrados por jugadores ARG.
"""
import httpx
import logging
from datetime import date

logger = logging.getLogger(__name__)

# Endpoint interno de la web ATP Tour (reverse engineered, estable desde 2022)
ATP_SCORES_JSON = "https://www.atptour.com/en/scores/current-results-ajax"
ATP_TODAY_JSON  = "https://www.atptour.com/en/scores/ajax/today-schedule"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*",
    "Referer": "https://www.atptour.com/en/scores/current",
    "X-Requested-With": "XMLHttpRequest",
}

# Jugadores argentinos activos ATP (normalizado sin tildes)
ARG_ATP = {
    "cerundolo", "francisco cerundolo", "etcheverry", "tomas etcheverry",
    "baez", "sebastian baez", "navone", "mariano navone",
    "zeballos", "horacio zeballos", "burruchaga", "roman burruchaga",
    "trungelliti", "marco trungelliti", "tirante", "thiago tirante",
    "ugo carabelli", "camilo ugo", "comesana", "francisco comesana",
    "juan manuel cerundolo", "juanma cerundolo",
    "diaz acosta", "facundo diaz acosta",
}


async def get_live_scores() -> list[dict]:
    """Partidos ATP en vivo o del día. Retorna [] si falla."""
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=12,
                                      follow_redirects=True) as c:
            r = await c.get(ATP_SCORES_JSON)
            r.raise_for_status()
            data = r.json()
            logger.info(f"[atp_live] raw keys: {list(data.keys())[:5]}")
            return _parse_atp_json(data)
    except Exception as e:
        logger.warning(f"[atp_live] live: {e}")
        return []


def _parse_atp_json(data: dict) -> list[dict]:
    results = []
    # ATP retorna {"completed": [...], "inProgress": [...], "upcoming": [...]}
    for section, status in [
        ("inProgress", "live"),
        ("completed", "finished"),
        ("upcoming", "upcoming"),
        ("scheduledMatches", "upcoming"),
    ]:
        for match in data.get(section, []) or []:
            parsed = _parse_match(match, status)
            if parsed:
                results.append(parsed)
    return results


def _parse_match(m: dict, default_status: str) -> dict | None:
    try:
        # Los nombres pueden estar en varios campos según la versión
        p1 = (m.get("player1", {}) or {})
        p2 = (m.get("player2", {}) or {})
        home = (
            p1.get("fullName") or p1.get("displayName") or
            p1.get("lastName") or m.get("homePlayer", "") or ""
        ).strip()
        away = (
            p2.get("fullName") or p2.get("displayName") or
            p2.get("lastName") or m.get("awayPlayer", "") or ""
        ).strip()

        if not home or not away:
            return None

        # Filtrar solo argentinos
        home_l = home.lower()
        away_l = away.lower()
        if not any(a in home_l or a in away_l for a in ARG_ATP):
            return None

        comp = (m.get("tournamentName") or m.get("tournament", {}).get("name", "")
                or "ATP Tour").strip()

        status = default_status
        status_raw = (m.get("matchStatus") or m.get("status") or "").lower()
        if "in progress" in status_raw or "live" in status_raw:
            status = "live"
        elif "finished" in status_raw or "complete" in status_raw:
            status = "finished"

        score_raw = m.get("score") or m.get("scoreDisplay") or ""

        return {
            "home": home,
            "away": away,
            "competition": comp,
            "home_score": None,
            "away_score": None,
            "score_detail": str(score_raw),
            "status": status,
            "minute": None,
            "start_time": m.get("startTime") or m.get("scheduledTime"),
            "source": "atptour",
            "raw": m,
        }
    except Exception:
        return None
