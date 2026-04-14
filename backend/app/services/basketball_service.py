from __future__ import annotations

import logging
import re
from bs4 import BeautifulSoup

from scraping.sources.cabb import get_lnb_html, parse_lnb

logger = logging.getLogger(__name__)


async def get_lnb_overview(competition: str = "liga-nacional") -> dict:
    """
    Retorna tabla + fixture para básquet argentino.
    competition hoy es informativo (default: liga-nacional),
    para permitir selector en frontend sin romper contrato.
    """
    html = await get_lnb_html()
    if not html:
        return {
            "competition": competition,
            "competition_label": "Liga Nacional",
            "standings": [],
            "fixtures": [],
            "source": "lnb",
            "error": "No se pudo obtener HTML de LNB",
        }

    fixtures_raw = parse_lnb(html)
    fixtures = [
        {
            "home": row.get("home", ""),
            "away": row.get("away", ""),
            "status": row.get("status", "upcoming"),
            "start_time": row.get("start_time"),
            "home_score": row.get("home_score"),
            "away_score": row.get("away_score"),
        }
        for row in fixtures_raw
    ]

    standings = _parse_lnb_standings(html)

    return {
        "competition": competition,
        "competition_label": "Liga Nacional",
        "standings": standings,
        "fixtures": fixtures,
        "source": "lnb",
    }


def _parse_lnb_standings(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")

    tables = soup.select("table")
    for table in tables:
        headers = [th.get_text(" ", strip=True).lower() for th in table.select("thead th")]
        header_text = " ".join(headers)
        if not any(k in header_text for k in ("equipo", "pts", "pj", "pos")):
            continue

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
    parsed: list[dict] = []

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

        parsed.append(
            {
                "position": pos or len(parsed) + 1,
                "team": team,
                "pj": pj,
                "pts": pts,
            }
        )

    return parsed[:20]


def _extract_team_name(cells: list[str]) -> str | None:
    for c in cells:
        txt = c.strip()
        if not txt:
            continue
        if txt.isdigit():
            continue
        if len(txt) <= 2:
            continue
        if re.fullmatch(r"[0-9\-\.]+", txt):
            continue
        return txt
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
    m = re.search(r"\d+", value)
    if not m:
        return None
    try:
        return int(m.group(0))
    except Exception:
        return None
