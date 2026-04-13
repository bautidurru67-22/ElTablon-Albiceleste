"""
FIH (Fédération Internationale de Hockey) — API JSON oficial.
https://www.fih.ch/ usa endpoints JSON internos para su web.
Retorna partidos del FIH Pro League, World Cup, etc.
"""
import httpx
import logging
from datetime import date

logger = logging.getLogger(__name__)

# Endpoint interno de la web FIH (reverse engineered, usado por su SPA)
FIH_MATCHES = "https://www.fih.ch/api/matches"
FIH_RESULTS = "https://www.fih.ch/api/results"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Referer": "https://www.fih.ch/",
    "Origin": "https://www.fih.ch",
}


async def get_today_matches() -> list[dict]:
    """Partidos FIH de hoy. Retorna [] si falla."""
    today = date.today().isoformat()
    results = []
    for url in [
        f"{FIH_MATCHES}?date={today}",
        f"{FIH_RESULTS}?date={today}",
        "https://www.fih.ch/api/fixtures?limit=20",
    ]:
        try:
            async with httpx.AsyncClient(headers=HEADERS, timeout=12,
                                          follow_redirects=True) as c:
                r = await c.get(url)
                r.raise_for_status()
                data = r.json()
                if isinstance(data, list):
                    results.extend(data)
                elif isinstance(data, dict):
                    results.extend(data.get("matches") or data.get("data") or [])
                logger.info(f"[fih] {url} → {len(results)}")
                if results:
                    break
        except Exception as e:
            logger.debug(f"[fih] {url}: {e}")

    return results


def parse_match(m: dict) -> dict | None:
    """Convierte match FIH al formato normalizable."""
    try:
        home = (m.get("homeTeam") or {}).get("name", "") or m.get("home_team", "") or ""
        away = (m.get("awayTeam") or {}).get("name", "") or m.get("away_team", "") or ""
        if not home or not away:
            return None

        status_raw = (m.get("status") or m.get("matchStatus") or "").lower()
        if "live" in status_raw or "progress" in status_raw:
            status = "live"
        elif "final" in status_raw or "finished" in status_raw or "complete" in status_raw:
            status = "finished"
        else:
            status = "upcoming"

        hs = m.get("homeScore") or m.get("home_score")
        as_ = m.get("awayScore") or m.get("away_score")
        try:
            hs = int(hs) if hs is not None else None
            as_ = int(as_) if as_ is not None else None
        except (ValueError, TypeError):
            hs = as_ = None

        comp = (m.get("competition") or m.get("tournament") or {})
        if isinstance(comp, dict):
            comp = comp.get("name", "FIH Hockey")

        return {
            "home": home.strip(),
            "away": away.strip(),
            "competition": comp or "FIH Hockey",
            "home_score": hs,
            "away_score": as_,
            "status": status,
            "minute": None,
            "start_time": m.get("startTime") or m.get("date"),
            "source": "fih",
            "raw": m,
        }
    except Exception:
        return None
