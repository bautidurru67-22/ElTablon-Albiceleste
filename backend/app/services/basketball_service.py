from __future__ import annotations

import logging
import re
import asyncio
from bs4 import BeautifulSoup

from scraping.sources.cabb import get_lnb_html, parse_lnb

logger = logging.getLogger(__name__)


async def _get_lnb_html_fast(timeout_s: float = 4.0) -> str | None:
    try:
        return await asyncio.wait_for(get_lnb_html(), timeout=timeout_s)
    except Exception:
        return None


async def get_lnb_overview(competition: str = "liga-nacional") -> dict:
    standings: list[dict] = []
    fixtures: list[dict] = []
    errors: list[str] = []

    html = await _get_lnb_html_fast()

    if html:
        try:
            raw = parse_lnb(html)
            fixtures = [
                {
                    "home": row.get("home", ""),
                    "away": row.get("away", ""),
                    "status": row.get("status", "upcoming"),
                    "start_time": row.get("start_time"),
                    "home_score": row.get("home_score"),
                    "away_score": row.get("away_score"),
                }
                for row in raw
                if row.get("home") and row.get("away")
            ]
        except Exception as e:
            errors.append(f"parse_lnb_error:{e}")

        try:
            standings = _parse_lnb_standings(html)
        except Exception as e:
            errors.append(f"parse_standings_error:{e}")
    else:
        errors.append("lnb_timeout_or_empty")

    # Fallback rápido a cache del deporte
    if not fixtures:
        try:
            from app.services.match_service import get_sport_hoy
            today = await asyncio.wait_for(get_sport_hoy("basquet"), timeout=3.5)
            fixtures = [
                {
                    "home": m.home_team,
                    "away": m.away_team,
                    "status": m.status,
                    "start_time": m.start_time,
                    "home_score": m.home_score,
                    "away_score": m.away_score,
                }
                for m in today
            ]
            if fixtures:
                errors.append("fixture_from_cache_fallback")
        except Exception as e:
            errors.append(f"cache_fallback_error:{e}")

    result = {
        "competition": competition,
        "competition_label": "Liga Nacional",
        "standings": standings,
        "fixtures": fixtures,
        "source": "lnb",
    }

    if errors:
        result["error"] = " | ".join(errors)

    return result


def _parse_lnb_standings(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    tables = soup.select("table")

    for table in tables:
        headers = [th.get_text(" ", strip=True).lower() for th in table.select("thead th")]
        head = " ".join(headers)
        if any(k in head for k in ("equipo", "pts", "pj", "pos")):
            parsed = _parse_table_rows(table)
            if parsed:
                return parsed

    for table in tables:
        parsed = _parse_table_rows(table)
        if parsed:
            return parsed

    return []


def _parse_table_rows(table) -> list[dict]:
    rows = table.select("tbody tr") or table.select("tr")
    out: list[dict] = []

    for row in rows:
        cells = [c.get_text(" ", strip=True) for c in row.select("td")]
        if len(cells) < 2:
            continue

        team = _extract_team_name(cells)
        if not team:
            continue

        pos = _first_int(cells[0]) if cells else None
        pj = _first_int(_find_metric(cells, ("pj", "jug")))
        pts = _first_int(_find_metric(cells, ("pts", "puntos")))

        if pj is None and len(cells) >= 4:
            pj = _first_int(cells[2])
        if pts is None and len(cells) >= 5:
            pts = _first_int(cells[4])

        out.append({
            "position": pos or len(out) + 1,
            "team": team,
            "pj": pj,
            "pts": pts,
        })

    return out[:20]


def _extract_team_name(cells: list[str]) -> str | None:
    for c in cells:
        t = c.strip()
        if not t:
            continue
        if t.isdigit():
            continue
        if len(t) <= 2:
            continue
        if re.fullmatch(r"[0-9\\-\\.]+", t):
            continue
        return t
    return None


def _find_metric(cells: list[str], keys: tuple[str, ...]) -> str:
    for c in cells:
        lc = c.lower()
        if any(k in lc for k in keys):
            return c
    return ""


def _first_int(value: str | None) -> int | None:
    if not value:
        return None
    m = re.search(r"\\d+", value)
    if not m:
        return None
    try:
        return int(m.group(0))
    except Exception:
        return None
