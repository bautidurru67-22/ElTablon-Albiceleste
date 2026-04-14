from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import unicodedata

from app.models.match import Match
from app.cache import cache


def _norm(s: str | None) -> str:
    s = (s or "").strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    return s


# Slugs y keywords por deporte/competencia
COMPETITION_MAP: dict[str, dict[str, dict[str, object]]] = {
    "futbol": {
        "mundial": {"label": "Mundial", "keywords": ["mundial", "world cup"]},
        "liga-profesional": {"label": "Liga Profesional", "keywords": ["liga profesional", "lpf", "superliga"]},
        "primera-nacional": {"label": "Primera Nacional", "keywords": ["primera nacional"]},
        "copa-argentina": {"label": "Copa Argentina", "keywords": ["copa argentina"]},
        "reserva": {"label": "Reserva", "keywords": ["reserva"]},
        "femenina": {"label": "1era División Femenina", "keywords": ["femenina"]},
        "juveniles": {"label": "Juveniles", "keywords": ["juvenil"]},
        "b-metro": {"label": "B Metro", "keywords": ["b metro", "primera b"]},
        "federal-a": {"label": "Federal A", "keywords": ["federal a"]},
        "federal-b": {"label": "Federal B", "keywords": ["federal b", "regional amateur"]},
        "primera-c": {"label": "Primera C", "keywords": ["primera c"]},
        "promocional": {"label": "Promocional Amateur", "keywords": ["promocional"]},
        "libertadores": {"label": "Copa Libertadores", "keywords": ["libertadores"]},
        "sudamericana": {"label": "Copa Sudamericana", "keywords": ["sudamericana"]},
    },
    "basquet": {
        "liga-nacional": {"label": "Liga Nacional", "keywords": ["liga nacional", "lnb"]},
        "liga-argentina": {"label": "Liga Argentina", "keywords": ["liga argentina"]},
        "liga-federal": {"label": "Liga Federal", "keywords": ["liga federal"]},
        "copa-super20": {"label": "Copa Súper 20", "keywords": ["super 20", "super20", "súper 20"]},
        "nba": {"label": "NBA", "keywords": ["nba"]},
        "fiba": {"label": "FIBA", "keywords": ["fiba"]},
        "seleccion": {"label": "Selección", "keywords": ["seleccion", "selection"]},
    },
}


async def _read_cache(key: str) -> list[Match]:
    data = await cache.get(key)
    if data is not None:
        return data
    data = await cache.get_last_valid(key)
    if data is not None:
        return data
    return []


def _competition_meta(sport: str, slug: str) -> dict[str, object]:
    sport_map = COMPETITION_MAP.get(sport, {})
    return sport_map.get(slug, {"label": slug.replace("-", " ").title(), "keywords": []})


def _filter_by_slug(matches: list[Match], sport: str, slug: str) -> list[Match]:
    meta = _competition_meta(sport, slug)
    keywords: list[str] = [str(k) for k in meta.get("keywords", [])]
    if not keywords:
        return matches
    out: list[Match] = []
    for m in matches:
        c = _norm(m.competition)
        if any(_norm(k) in c for k in keywords):
            out.append(m)
    return out


def _sort_matches(matches: list[Match]) -> list[Match]:
    order = {"live": 0, "upcoming": 1, "finished": 2}
    return sorted(matches, key=lambda m: (order.get(m.status, 9), m.start_time or ""))


async def get_competition_fixture(sport: str, slug: str) -> dict:
    all_today = await _read_cache(f"today:{sport}")
    filtered = _filter_by_slug(all_today, sport, slug)
    filtered = _sort_matches(filtered)

    return {
        "sport": sport,
        "slug": slug,
        "competition": _competition_meta(sport, slug).get("label"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(filtered),
        "matches": [m.model_dump() for m in filtered],
    }


async def get_competition_table(sport: str, slug: str) -> dict:
    # Tabla inferida desde resultados cacheados del día (MVP funcional)
    all_today = await _read_cache(f"today:{sport}")
    filtered = _filter_by_slug(all_today, sport, slug)

    rows = defaultdict(lambda: {"team": "", "pj": 0, "pg": 0, "pe": 0, "pp": 0, "gf": 0, "gc": 0, "pts": 0})

    for m in filtered:
        if m.status != "finished" or m.home_score is None or m.away_score is None:
            continue

        h = m.home_team
        a = m.away_team
        hs = int(m.home_score)
        aw = int(m.away_score)

        rows[h]["team"] = h
        rows[a]["team"] = a

        rows[h]["pj"] += 1
        rows[a]["pj"] += 1
        rows[h]["gf"] += hs
        rows[h]["gc"] += aw
        rows[a]["gf"] += aw
        rows[a]["gc"] += hs

        if hs > aw:
            rows[h]["pg"] += 1
            rows[h]["pts"] += 3
            rows[a]["pp"] += 1
        elif hs < aw:
            rows[a]["pg"] += 1
            rows[a]["pts"] += 3
            rows[h]["pp"] += 1
        else:
            rows[h]["pe"] += 1
            rows[a]["pe"] += 1
            rows[h]["pts"] += 1
            rows[a]["pts"] += 1

    table = list(rows.values())
    for r in table:
        r["dg"] = r["gf"] - r["gc"]

    table.sort(key=lambda r: (r["pts"], r["dg"], r["gf"]), reverse=True)

    for i, r in enumerate(table, start=1):
        r["pos"] = i

    return {
        "sport": sport,
        "slug": slug,
        "competition": _competition_meta(sport, slug).get("label"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "rows": table,
    }


async def get_competition_scorers(sport: str, slug: str) -> dict:
    # Placeholder consistente (hasta conectar feed de goleadores real)
    # Mantiene contrato API para no romper frontend.
    return {
        "sport": sport,
        "slug": slug,
        "competition": _competition_meta(sport, slug).get("label"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "rows": [],
        "note": "Sin feed de goleadores conectado aún para esta competencia.",
    }


async def list_competitions(sport: str) -> dict:
    sport_map = COMPETITION_MAP.get(sport, {})
    return {
        "sport": sport,
        "items": [
            {"slug": slug, "label": data["label"]}
            for slug, data in sport_map.items()
        ],
    }
