"""
TheSportsDB v1 — API gratuita.
Free key: "3" (funciona para búsquedas básicas, NO para livescores)
Key "123" = test key, mismos límites.
eventsday.php funciona para algunas ligas en free tier.
"""
import httpx
import logging
from datetime import date

logger = logging.getLogger(__name__)

BASE = "https://www.thesportsdb.com/api/v1/json/3"  # free key = 3

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; TablonAlbiceleste/1.0)",
    "Accept": "application/json",
}

# IDs validados en TheSportsDB
LEAGUE_IDS = {
    # Fútbol
    4406: "Liga Profesional Argentina",
    4500: "Copa Libertadores",
    # Básquet
    4387: "NBA",
    4966: "LNB Argentina",
    # Rugby
    5042: "Rugby Championship",
    # Hockey
    5066: "FIH Pro League",
    # Tenis
    4926: "ATP Tour",
}


async def get_events_today(league_id: int) -> list[dict]:
    """Partidos de hoy para una liga. Retorna [] si falla o no hay datos."""
    today = date.today().strftime("%Y-%m-%d")
    url = f"{BASE}/eventsday.php?d={today}&l={league_id}"
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=10,
                                      follow_redirects=True) as c:
            r = await c.get(url)
            r.raise_for_status()
            data = r.json()
            events = data.get("events") or []
            logger.info(f"[tsdb] league={league_id} → {len(events)}")
            return events
    except Exception as e:
        logger.warning(f"[tsdb] league={league_id}: {e}")
        return []


async def get_next_events(league_id: int) -> list[dict]:
    """Próximos 15 eventos de una liga (más confiable que eventsday)."""
    url = f"{BASE}/eventsnextleague.php?id={league_id}"
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=10,
                                      follow_redirects=True) as c:
            r = await c.get(url)
            r.raise_for_status()
            data = r.json()
            events = data.get("events") or []
            logger.info(f"[tsdb/next] league={league_id} → {len(events)}")
            return events
    except Exception as e:
        logger.warning(f"[tsdb/next] league={league_id}: {e}")
        return []


async def get_last_events(league_id: int) -> list[dict]:
    """Últimos 15 resultados de una liga."""
    url = f"{BASE}/eventspastleague.php?id={league_id}"
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=10,
                                      follow_redirects=True) as c:
            r = await c.get(url)
            r.raise_for_status()
            data = r.json()
            events = data.get("events") or []
            logger.info(f"[tsdb/past] league={league_id} → {len(events)}")
            return events
    except Exception as e:
        logger.warning(f"[tsdb/past] league={league_id}: {e}")
        return []


def parse_event(ev: dict, sport: str) -> dict:
    """Convierte evento TheSportsDB al formato normalizable."""
    home = (ev.get("strHomeTeam") or "").strip()
    away = (ev.get("strAwayTeam") or "").strip()
    comp = (ev.get("strLeague") or "").strip()

    status_raw = (ev.get("strStatus") or "").lower()
    if status_raw in ("match finished", "ft", "aet", "pen", "finished"):
        status = "finished"
    elif status_raw in ("in progress", "live", "ht", "inprogress"):
        status = "live"
    else:
        status = "upcoming"

    hs = ev.get("intHomeScore")
    as_ = ev.get("intAwayScore")
    try:
        hs = int(hs) if hs not in (None, "", "null") else None
        as_ = int(as_) if as_ not in (None, "", "null") else None
    except (ValueError, TypeError):
        hs = as_ = None

    # Hora UTC → ARG
    start_time_arg = None
    time_raw = ev.get("strTime") or ev.get("strTimeLocal") or ""
    if time_raw and ":" in time_raw:
        try:
            h, m = int(time_raw[:2]), int(time_raw[3:5])
            start_time_arg = f"{(h - 3) % 24:02d}:{m:02d}"
        except Exception:
            pass

    return {
        "home": home,
        "away": away,
        "competition": comp,
        "home_score": hs,
        "away_score": as_,
        "status": status,
        "minute": None,
        "start_time": start_time_arg,
        "source": "thesportsdb",
        "raw": ev,
    }
