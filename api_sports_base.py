"""
api_sports_base.py
Base común para todos los scrapers de El Tablón Albiceleste.
Maneja: HTTP con retry, timezone ART, NormalizedMatch, caché en memoria.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field, asdict
from typing import Optional
import httpx

logger = logging.getLogger("tablon.scraper")

# ─── TIMEZONE ────────────────────────────────────────────────
ART = timezone(timedelta(hours=-3))

def now_art() -> datetime:
    return datetime.now(ART)

def today_art() -> str:
    """Fecha actual en Argentina — YYYY-MM-DD. Nunca usa UTC."""
    return now_art().strftime("%Y-%m-%d")

def time_art(iso_utc: str) -> str:
    """Convierte ISO UTC a HH:MM en horario argentino."""
    try:
        dt = datetime.fromisoformat(iso_utc.replace("Z", "+00:00"))
        return dt.astimezone(ART).strftime("%H:%M")
    except Exception:
        return "--:--"

def date_art(iso_utc: str) -> str:
    """Convierte ISO UTC a YYYY-MM-DD en horario argentino."""
    try:
        dt = datetime.fromisoformat(iso_utc.replace("Z", "+00:00"))
        return dt.astimezone(ART).strftime("%Y-%m-%d")
    except Exception:
        return today_art()

# ─── MODELO UNIFICADO ────────────────────────────────────────
@dataclass
class NormalizedMatch:
    sport: str
    competition: str
    home_team: str
    away_team: str
    home_score: Optional[int]
    away_score: Optional[int]
    status: str                  # "live" | "upcoming" | "finished"
    start_time: str              # HH:MM en ART
    date: str                    # YYYY-MM-DD en ART
    minute: Optional[str] = None
    period: Optional[str] = None
    venue: Optional[str] = None
    broadcast: list = field(default_factory=list)
    argentina_relevance: str = "none"   # "seleccion"|"club_arg"|"jugador_arg"|"none"
    argentina_team: Optional[str] = None
    source: str = "unknown"
    updated_at: str = field(default_factory=lambda: now_art().isoformat())
    home_logo: Optional[str] = None
    away_logo: Optional[str] = None
    match_id: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

# ─── HTTP CON RETRY ─────────────────────────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
}

async def fetch_json(
    url: str,
    headers: Optional[dict] = None,
    timeout: int = 10,
    retries: int = 2,
) -> Optional[dict]:
    h = {**HEADERS, **(headers or {})}
    for attempt in range(retries + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                resp = await client.get(url, headers=h)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as e:
            logger.warning(f"[fetch_json] HTTP {e.response.status_code} — {url}")
            if e.response.status_code in (429, 503):
                await asyncio.sleep(2 ** attempt)
            else:
                return None
        except Exception as e:
            if attempt < retries:
                await asyncio.sleep(1.5 * (attempt + 1))
            else:
                logger.error(f"[fetch_json] FAILED {url}: {e}")
                return None
    return None

async def fetch_text(
    url: str,
    headers: Optional[dict] = None,
    timeout: int = 10,
    retries: int = 2,
) -> Optional[str]:
    h = {**HEADERS, "Accept": "text/html,*/*", **(headers or {})}
    for attempt in range(retries + 1):
        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                resp = await client.get(url, headers=h)
                resp.raise_for_status()
                return resp.text
        except Exception as e:
            if attempt < retries:
                await asyncio.sleep(1.5 * (attempt + 1))
            else:
                logger.error(f"[fetch_text] FAILED {url}: {e}")
                return None
    return None

# ─── CACHÉ EN MEMORIA ────────────────────────────────────────
from typing import Any
import time

_cache: dict[str, tuple[Any, float]] = {}  # key → (data, expires_at)

def cache_get(key: str) -> Optional[Any]:
    entry = _cache.get(key)
    if entry is None:
        return None
    data, expires_at = entry
    if time.monotonic() > expires_at:
        del _cache[key]
        return None
    return data

def cache_set(key: str, data: Any, ttl_seconds: int) -> None:
    _cache[key] = (data, time.monotonic() + ttl_seconds)

def cache_invalidate_prefix(prefix: str) -> int:
    keys = [k for k in _cache if k.startswith(prefix)]
    for k in keys:
        del _cache[k]
    return len(keys)

TTL = {
    "live":      20,    # 20 segundos
    "today":     90,    # 90 segundos
    "finished":  3600,  # 1 hora
    "standings": 600,   # 10 minutos
    "error":     15,    # 15s antes de reintentar fuente fallida
}

# ─── DETECTOR DE RELEVANCIA ARGENTINA ───────────────────────
ARG_TEAM_KEYWORDS = {
    # Selección
    "argentina", "albiceleste", "selección argentina",
    # Fútbol clubes
    "river plate", "boca juniors", "racing", "independiente",
    "san lorenzo", "huracán", "estudiantes", "gimnasia",
    "talleres", "belgrano", "vélez", "lanús", "banfield",
    "tigre", "defensa", "platense", "central córdoba",
    "rosario central", "newell", "godoy cruz", "arsenal",
    "colón", "unión", "atlético tucumán", "sarmiento",
    "barracas central", "riestra", "instituto", "ferro",
    # Básquet
    "peñarol", "quimsa", "obras",
    # Rugby
    "jaguares", "pumas", "casi", "sic", "newman", "hindú",
    # Hockey
    "leonas", "leones",
}

ARG_PLAYER_KEYWORDS = {
    # Tenis
    "cerundolo", "cerúndolo", "etcheverry", "baez", "báez",
    "navone", "bagnis", "cachin", "cachín", "podoroska",
    "zeballos", "gonzalez", "sierra", "riera",
    # Fútbol
    "messi", "di maría", "dybala", "lautaro", "julián álvarez",
    "de paul", "mac allister", "enzo fernández", "molina",
    "lisandro martínez", "romero", "martínez dibu",
    # Básquet
    "campazzo", "bolmaro", "deck", "laprovittola",
}

def detect_argentina_relevance(
    home: str,
    away: str,
    competition: str = "",
    player_names: list[str] = None,
) -> tuple[str, Optional[str]]:
    """
    Retorna (argentina_relevance, argentina_team).
    relevance: "seleccion" | "club_arg" | "jugador_arg" | "none"
    """
    home_l = home.lower()
    away_l = away.lower()
    comp_l = competition.lower()

    # Selección primero
    if "argentina" in home_l or "argentina" in away_l:
        team = home if "argentina" in home_l else away
        return "seleccion", team

    # Clubs argentinos
    for kw in ARG_TEAM_KEYWORDS:
        if kw in home_l:
            return "club_arg", home
        if kw in away_l:
            return "club_arg", away

    # Jugadores argentinos
    search_text = f"{home_l} {away_l} {' '.join(player_names or []).lower()}"
    for kw in ARG_PLAYER_KEYWORDS:
        if kw in search_text:
            return "jugador_arg", None

    return "none", None
