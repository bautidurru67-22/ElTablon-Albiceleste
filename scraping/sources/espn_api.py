"""
ESPN API pública (no oficial, estable desde 2015).
Sin key, sin auth, funciona desde Railway.
Cubre: fútbol, básquet, tenis, rugby, golf, hockey, MMA.

Formato: https://site.api.espn.com/apis/site/v2/sports/{sport}/{league}/scoreboard
"""
import httpx
import logging
from datetime import date, datetime, timezone

logger = logging.getLogger(__name__)

BASE = "https://site.api.espn.com/apis/site/v2/sports"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
    "Origin": "https://www.espn.com",
    "Referer": "https://www.espn.com/",
}

# Slugs ESPN para Argentina y deportes relevantes
# Formato: {sport_interno: (espn_sport, espn_league)}
ENDPOINTS = {
    # ── Fútbol ─────────────────────────────────────────────────────────
    "futbol_liga_prof":      ("soccer", "arg.1"),          # Liga Profesional Argentina
    "futbol_libertadores":   ("soccer", "conmebol.libertadores"),
    "futbol_sudamericana":   ("soccer", "conmebol.sudamericana"),
    "futbol_copa_argentina": ("soccer", "arg.copa_argentina"),
    "futbol_primera_nac":    ("soccer", "arg.2"),          # Primera Nacional
    "futbol_laliga":         ("soccer", "esp.1"),
    "futbol_premier":        ("soccer", "eng.1"),
    "futbol_serie_a":        ("soccer", "ita.1"),
    "futbol_bundesliga":     ("soccer", "ger.1"),
    "futbol_champions":      ("soccer", "uefa.champions"),
    # ── Básquet ────────────────────────────────────────────────────────
    "basquet_nba":           ("basketball", "nba"),
    # ── Tenis ──────────────────────────────────────────────────────────
    "tenis_atp":             ("tennis", "atp"),
    "tenis_wta":             ("tennis", "wta"),
    # ── Golf ───────────────────────────────────────────────────────────
    "golf_pga":              ("golf", "pga"),
}

# Agrupamiento para fácil acceso por deporte interno
SPORT_ENDPOINTS = {
    "futbol":  ["futbol_liga_prof", "futbol_libertadores", "futbol_sudamericana",
                "futbol_copa_argentina", "futbol_primera_nac",
                "futbol_laliga", "futbol_premier", "futbol_serie_a",
                "futbol_bundesliga", "futbol_champions"],
    "basquet": ["basquet_nba"],
    "tenis":   ["tenis_atp", "tenis_wta"],
    "golf":    ["golf_pga"],
}

# Mapeo de estado ESPN → nuestro estado
STATUS_MAP = {
    "STATUS_SCHEDULED":     "upcoming",
    "STATUS_IN_PROGRESS":   "live",
    "STATUS_HALFTIME":      "live",
    "STATUS_END_PERIOD":    "live",
    "STATUS_FINAL":         "finished",
    "STATUS_FULL_TIME":     "finished",
    "STATUS_POSTPONED":     "finished",
    "STATUS_CANCELED":      "finished",
    "STATUS_SUSPENDED":     "finished",
}


async def get_scoreboard(espn_sport: str, espn_league: str) -> dict:
    """Retorna scoreboard de una liga. Retorna {} si falla."""
    url = f"{BASE}/{espn_sport}/{espn_league}/scoreboard"
    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=12,
                                      follow_redirects=True) as c:
            r = await c.get(url)
            r.raise_for_status()
            data = r.json()
            events = data.get("events", [])
            logger.info(f"[espn] {espn_sport}/{espn_league} → {len(events)} events")
            return data
    except httpx.HTTPStatusError as e:
        logger.warning(f"[espn] HTTP {e.response.status_code} {espn_sport}/{espn_league}")
        return {}
    except Exception as e:
        logger.warning(f"[espn] {espn_sport}/{espn_league}: {e}")
        return {}


async def get_sport_events(sport: str) -> list[dict]:
    """
    Retorna todos los eventos ESPN para un deporte.
    Concatena todos los endpoints del deporte.
    """
    endpoints = SPORT_ENDPOINTS.get(sport, [])
    all_events = []
    seen_ids = set()

    for endpoint_key in endpoints:
        espn_sport, espn_league = ENDPOINTS[endpoint_key]
        data = await get_scoreboard(espn_sport, espn_league)
        for ev in data.get("events", []):
            eid = ev.get("id", "")
            if eid not in seen_ids:
                seen_ids.add(eid)
                ev["_league_key"] = endpoint_key
                all_events.append(ev)

    return all_events


def parse_event(ev: dict) -> dict | None:
    """Convierte un evento ESPN al formato normalizable."""
    try:
        competitions = ev.get("competitions", [])
        if not competitions:
            return None
        comp = competitions[0]

        competitors = comp.get("competitors", [])
        if len(competitors) < 2:
            return None

        # ESPN siempre pone home primero
        home_team = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
        away_team = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])

        home = (home_team.get("team", {}).get("displayName") or
                home_team.get("team", {}).get("shortDisplayName") or "").strip()
        away = (away_team.get("team", {}).get("displayName") or
                away_team.get("team", {}).get("shortDisplayName") or "").strip()

        if not home or not away:
            return None

        # Liga/competencia
        league = ev.get("season", {}).get("displayName", "")
        league_from_name = ev.get("name", "")
        comp_name = (ev.get("_league_key", "").replace("_", " ").title() or
                     league or league_from_name or "").strip()

        # Estado
        status_obj = comp.get("status", {})
        status_type = status_obj.get("type", {}).get("name", "STATUS_SCHEDULED")
        status = STATUS_MAP.get(status_type, "upcoming")

        # Minuto/período
        minute = None
        if status == "live":
            period = status_obj.get("period", 0)
            display_clock = status_obj.get("displayClock", "")
            desc = status_obj.get("type", {}).get("shortDetail", "")
            minute = desc or (f"{period}T {display_clock}".strip() if period else display_clock)

        # Marcador
        hs = as_ = None
        if status in ("live", "finished"):
            try:
                hs = int(home_team.get("score", 0))
                as_ = int(away_team.get("score", 0))
            except (ValueError, TypeError):
                pass

        # Hora ARG
        start_time_arg = None
        date_raw = comp.get("date", "") or ev.get("date", "")
        if date_raw:
            try:
                dt = datetime.fromisoformat(date_raw.replace("Z", "+00:00"))
                start_time_arg = f"{(dt.hour - 3) % 24:02d}:{dt.minute:02d}"
            except Exception:
                pass

        # Canal de TV (primer broadcast disponible)
        broadcasts = comp.get("broadcasts", [])
        broadcast = None
        if broadcasts:
            names = broadcasts[0].get("names", [])
            broadcast = names[0] if names else None

        return {
            "home": home,
            "away": away,
            "competition": comp_name,
            "home_score": hs,
            "away_score": as_,
            "status": status,
            "minute": minute,
            "start_time": start_time_arg,
            "broadcast": broadcast,
            "source": "espn",
            "raw": ev,
        }
    except Exception as e:
        logger.debug(f"[espn/parse] {e}")
        return None
