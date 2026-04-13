"""
TheSportsDB — API gratuita sin key para la mayoría de endpoints.
https://www.thesportsdb.com/api.php
Retorna JSON real para fútbol, tenis, básquet, hockey, rugby, golf, etc.
Clave pública "3" funciona para búsquedas básicas.
"""
import httpx
import logging
from datetime import date

logger = logging.getLogger(__name__)

BASE = "https://www.thesportsdb.com/api/v1/json/3"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; TablonAlbiceleste/1.0)",
    "Accept": "application/json",
}

# League IDs en TheSportsDB para ligas argentinas y relevantes
LEAGUE_IDS = {
    # Fútbol Argentina
    "liga_profesional": 4406,
    "copa_argentina":   4411,
    "copa_libertadores": 4500,
    # Básquet
    "nba": 4387,
    "lnb_arg": 4966,
    # Rugby
    "rugby_championship": 5042,
    # Hockey FIH Pro League
    "fih_pro_league_m": 5066,
    "fih_pro_league_w": 5067,
    # Tenis ATP
    "atp": 4926,
    "wta": 4927,
}


async def get_events_today(league_id: int) -> list[dict]:
    """Partidos de hoy para una liga. Retorna [] si falla."""
    today = date.today().strftime("%Y-%m-%d")
    url = f"{BASE}/eventsday.php?d={today}&l={league_id}"
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=12, follow_redirects=True) as c:
            r = await c.get(url)
            r.raise_for_status()
            data = r.json()
            events = data.get("events") or []
            logger.info(f"[thesportsdb] league={league_id} → {len(events)} eventos")
            return events
    except Exception as e:
        logger.warning(f"[thesportsdb] league={league_id}: {e}")
        return []


async def get_events_by_round(league_id: int, season: str, round_n: int) -> list[dict]:
    url = f"{BASE}/eventsround.php?id={league_id}&r={round_n}&s={season}"
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=12, follow_redirects=True) as c:
            r = await c.get(url)
            r.raise_for_status()
            return r.json().get("events") or []
    except Exception as e:
        logger.warning(f"[thesportsdb] eventsround {league_id}: {e}")
        return []


def parse_event(ev: dict, sport: str) -> dict:
    """Convierte un evento TheSportsDB al formato normalizable."""
    home = ev.get("strHomeTeam", "") or ""
    away = ev.get("strAwayTeam", "") or ""
    comp = ev.get("strLeague", "") or ""

    status_raw = (ev.get("strStatus") or "").lower()
    if status_raw in ("match finished", "ft", "aet", "pen"):
        status = "finished"
    elif status_raw in ("in progress", "live", "ht"):
        status = "live"
    else:
        status = "upcoming"

    hs = ev.get("intHomeScore")
    as_ = ev.get("intAwayScore")
    try:
        hs = int(hs) if hs not in (None, "") else None
        as_ = int(as_) if as_ not in (None, "") else None
    except (ValueError, TypeError):
        hs = as_ = None

    # Hora: strTime viene en UTC "HH:MM:SS+00:00"
    start_time_arg = None
    time_raw = ev.get("strTime", "") or ""
    if time_raw and ":" in time_raw:
        try:
            h = int(time_raw[:2])
            m = int(time_raw[3:5])
            start_time_arg = f"{(h - 3) % 24:02d}:{m:02d}"
        except Exception:
            pass

    return {
        "home": home.strip(),
        "away": away.strip(),
        "competition": comp.strip(),
        "home_score": hs,
        "away_score": as_,
        "status": status,
        "minute": None,
        "start_time": start_time_arg,
        "source": "thesportsdb",
        "raw": ev,
    }
