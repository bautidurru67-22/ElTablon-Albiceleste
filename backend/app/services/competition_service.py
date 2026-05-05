from __future__ import annotations

import os
import re
import unicodedata
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Any

import httpx
from bs4 import BeautifulSoup

from app.services.football_service import get_football_overview
from app.services.basketball_service import get_lnb_overview

logger = logging.getLogger(__name__)
AR_TZ = ZoneInfo("America/Argentina/Buenos_Aires")

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

COMPETITION_MAP: dict[str, dict[str, dict[str, Any]]] = {
    "futbol": {
        "liga-profesional-argentina": {"label": "Liga Profesional", "keywords": ["liga profesional", "lpf", "superliga"]},
        "primera-nacional": {"label": "Primera Nacional", "keywords": ["primera nacional"]},
        "b-metro": {"label": "B Metro", "keywords": ["b metro", "primera b"]},
        "primera-c": {"label": "Primera C", "keywords": ["primera c"]},
        "federal-a": {"label": "Federal A", "keywords": ["federal a"]},
        "copa-argentina": {"label": "Copa Argentina", "keywords": ["copa argentina"]},
        "libertadores": {"label": "Copa Libertadores", "keywords": ["libertadores"]},
        "sudamericana": {"label": "Copa Sudamericana", "keywords": ["sudamericana"]},
    },
    "basquet": {
        "liga-nacional": {"label": "Liga Nacional", "keywords": ["liga nacional", "lnb"]},
        "liga-argentina": {"label": "Liga Argentina", "keywords": ["liga argentina"]},
        "liga-federal": {"label": "Liga Federal", "keywords": ["liga federal"]},
    },
}

COMPETITION_ALIASES = {
    "futbol": {
        "liga-profesional": "liga-profesional-argentina",
        "primera-nacional-argentina": "primera-nacional",
    }
}


def resolve_competition_slug(sport: str, slug: str) -> str:
    return COMPETITION_ALIASES.get(sport, {}).get(slug, slug)


def _norm(s: str | None) -> str:
    s = (s or "").strip().lower()
    s = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn")


def _safe_int(v: Any) -> int | None:
    if v is None:
        return None
    try:
        return int(v)
    except Exception:
        m = re.search(r"-?\d+", str(v))
        return int(m.group(0)) if m else None


def _to_arg_datetime(value: str | None) -> str | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.astimezone(AR_TZ).isoformat()
    except Exception:
        return value


def _map_status(status: str | None) -> str:
    s = (status or "").lower()
    mp = {
        "upcoming": "programado",
        "scheduled": "programado",
        "ns": "programado",
        "live": "en_vivo",
        "1h": "en_vivo",
        "ht": "en_vivo",
        "2h": "en_vivo",
        "finished": "finalizado",
        "ft": "finalizado",
        "suspended": "suspendido",
        "postponed": "postergado",
        "pst": "postergado",
    }
    return mp.get(s, s or "programado")


def _is_placeholder_key(key: str) -> bool:
    if not key:
        return True
    bad_prefixes = ("TU_", "YOUR_", "REPLACE_", "CHANGE_")
    bad_exact = {"TU_API_KEY_REAL", "TU_KEY_REAL_DE_API_FOOTBALL", "API_KEY", "test"}
    return key in bad_exact or key.startswith(bad_prefixes)


def _make_attempt(source: str, ok: bool, reason: str | None = None, http_status: int | None = None) -> dict:
    d = {"source": source, "ok": ok}
    if reason:
        d["reason"] = reason
    if http_status is not None:
        d["http_status"] = http_status
    return d


def _empty_payload(sport: str, competition_label: str, attempted: list[dict], error: str) -> dict:
    return {
        "sport": sport,
        "competition": competition_label,
        "season": datetime.now().year,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source_used": None,
        "sources_attempted": attempted,
        "standings": [],
        "fixtures": [],
        "groups": [],
        "error": error,
    }


def _normalize_from_service_payload(sport: str, slug: str, raw: dict, source_name: str) -> tuple[list[dict], list[dict]]:
    standings: list[dict] = []
    fixtures: list[dict] = []

    for r in raw.get("standings", []) or []:
        standings.append({
            "position": r.get("position") or len(standings) + 1,
            "team_name": r.get("team") or r.get("team_name"),
            "team_logo": r.get("team_logo"),
            "played": r.get("played") or r.get("pj"),
            "won": r.get("won"),
            "drawn": r.get("drawn"),
            "lost": r.get("lost"),
            "points": r.get("points") or r.get("pts"),
            "goals_for": r.get("goals_for"),
            "goals_against": r.get("goals_against"),
            "goal_difference": r.get("goal_diff") if r.get("goal_diff") is not None else r.get("goal_difference"),
            "recent_results": r.get("form") or r.get("recent_results"),
            "group": r.get("group_name") or r.get("group"),
            # basket extras
            "percentage": r.get("percentage"),
            "points_for": r.get("points_for"),
            "points_against": r.get("points_against"),
            "difference": r.get("difference"),
            "conference": r.get("conference"),
        })

    for i, f in enumerate(raw.get("fixtures", []) or []):
        fixtures.append({
            "id": f"{sport}-{slug}-{source_name}-{i}",
            "sport": sport,
            "competition": raw.get("competition_label"),
            "round": f.get("round"),
            "group": f.get("group"),
            "home_team": f.get("home") or f.get("home_team"),
            "away_team": f.get("away") or f.get("away_team"),
            "home_logo": f.get("home_logo"),
            "away_logo": f.get("away_logo"),
            "home_score": f.get("home_score"),
            "away_score": f.get("away_score"),
            "status": _map_status(f.get("status")),
            "datetime_arg": _to_arg_datetime(f.get("date") or f.get("start_time") or f.get("datetime_arg")),
            "venue": f.get("venue"),
            "source": source_name,
            "match_url": f.get("match_url"),
        })

    standings = [r for r in standings if r.get("team_name")]
    fixtures = [f for f in fixtures if f.get("home_team") and f.get("away_team")]
    return standings, fixtures


# ─────────────────────────────────────────────────────────────────────────────
# SCRAPERS: FALLBACKS REALES (HTTP + parse defensivo)
# ─────────────────────────────────────────────────────────────────────────────

async def _fetch_html(url: str, timeout_s: float = 8.0) -> tuple[int | None, str]:
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(timeout_s, connect=4.0),
            follow_redirects=True,
            headers={"User-Agent": UA, "Accept-Language": "es-AR,es;q=0.9,en;q=0.8"},
        ) as client:
            r = await client.get(url)
            return r.status_code, r.text if r.status_code < 500 else ""
    except Exception:
        return None, ""


def _first_text(el) -> str:
    return el.get_text(" ", strip=True) if el else ""


def _extract_fixtures_from_tables(
    html: str,
    sport: str,
    competition_label: str,
    source_name: str,
) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    fixtures: list[dict] = []
    rows = soup.select("table tr")
    if not rows:
        rows = soup.select("div, li")

    for i, row in enumerate(rows):
        txt = _first_text(row)
        if not txt:
            continue

        # Parse defensivo "Equipo A vs Equipo B" o "Equipo A - Equipo B"
        m = re.search(r"([A-Za-zÁÉÍÓÚÑáéíóúñ0-9\.\s]+)\s(?:vs|v\.|-\s)\s([A-Za-zÁÉÍÓÚÑáéíóúñ0-9\.\s]+)", txt)
        if not m:
            continue

        home = m.group(1).strip()
        away = m.group(2).strip()

        # score opcional
        sm = re.search(r"(\d+)\s*[-:]\s*(\d+)", txt)
        hs = _safe_int(sm.group(1)) if sm else None
        as_ = _safe_int(sm.group(2)) if sm else None
        status = "finalizado" if sm else "programado"

        fixtures.append({
            "id": f"{sport}-{source_name}-html-{i}",
            "sport": sport,
            "competition": competition_label,
            "round": None,
            "group": None,
            "home_team": home,
            "away_team": away,
            "home_logo": None,
            "away_logo": None,
            "home_score": hs,
            "away_score": as_,
            "status": status,
            "datetime_arg": None,
            "venue": None,
            "source": source_name,
            "match_url": None,
        })

    return fixtures


def _extract_standings_from_tables(
    html: str,
    sport: str,
) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    standings: list[dict] = []
    tables = soup.select("table")
    for table in tables:
        rows = table.select("tr")
        for tr in rows:
            tds = tr.select("td")
            if len(tds) < 3:
                continue
            cells = [_first_text(td) for td in tds]
            team = None
            for c in cells:
                if c and len(c) > 2 and not c.isdigit():
                    if not re.fullmatch(r"[-\d\.:]+", c):
                        team = c
                        break
            if not team:
                continue

            pos = _safe_int(cells[0]) or len(standings) + 1
            played = _safe_int(cells[2]) if len(cells) > 2 else None
            won = _safe_int(cells[3]) if len(cells) > 3 else None
            drawn = _safe_int(cells[4]) if len(cells) > 4 else None
            lost = _safe_int(cells[5]) if len(cells) > 5 else None
            points = _safe_int(cells[-1]) if cells else None

            row = {
                "position": pos,
                "team_name": team,
                "team_logo": None,
                "played": played,
                "won": won,
                "drawn": drawn if sport == "futbol" else None,
                "lost": lost,
                "points": points,
                "goals_for": None,
                "goals_against": None,
                "goal_difference": None,
                "recent_results": None,
                "group": None,
                # basket extras
                "percentage": None,
                "points_for": None,
                "points_against": None,
                "difference": None,
                "conference": None,
            }
            standings.append(row)

    # dedupe por team_name
    out = []
    seen = set()
    for r in standings:
        k = _norm(r["team_name"])
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    return out


async def _try_lpf_oficial(slug: str) -> tuple[list[dict], list[dict], str | None]:
    # URL foco pedido
    url = "https://www.ligaprofesional.ar/torneo-apertura-2026/"
    status, html = await _fetch_html(url)
    if status is None:
        return [], [], "network_error"
    if status >= 400:
        return [], [], f"http_{status}"
    fixtures = _extract_fixtures_from_tables(html, "futbol", "Liga Profesional", "lpf_oficial")
    standings = _extract_standings_from_tables(html, "futbol")
    return standings, fixtures, None


async def _try_promiedos(slug: str, sport: str) -> tuple[list[dict], list[dict], str | None]:
    # Mapeo real de slugs Promiedos (aproximado defensivo)
    prom_map = {
        "liga-profesional-argentina": "https://www.promiedos.com.ar/league/liga-profesional/hc",
        "primera-nacional": "https://www.promiedos.com.ar/league/primera-nacional/hc",
        "b-metro": "https://www.promiedos.com.ar/league/primera-b/hc",
        "primera-c": "https://www.promiedos.com.ar/league/primera-c/hc",
        "federal-a": "https://www.promiedos.com.ar/league/federal-a/hc",
        "copa-argentina": "https://www.promiedos.com.ar/league/copa-argentina/hc",
        "liga-nacional": "https://www.promiedos.com.ar/basquet",
        "liga-argentina": "https://www.promiedos.com.ar/basquet",
        "liga-federal": "https://www.promiedos.com.ar/basquet",
    }
    url = prom_map.get(slug)
    if not url:
        return [], [], "slug_not_mapped"

    status, html = await _fetch_html(url)
    if status is None:
        return [], [], "network_error"
    if status >= 400:
        return [], [], f"http_{status}"

    fixtures = _extract_fixtures_from_tables(html, sport, COMPETITION_MAP[sport][slug]["label"], "promiedos")
    standings = _extract_standings_from_tables(html, sport)
    return standings, fixtures, None


async def _try_espn_generic(slug: str, sport: str) -> tuple[list[dict], list[dict], str | None]:
    # Fallback HTML genérico ESPN (defensivo)
    # Nota: parse genérico para no hardcodear partidos.
    url = "https://www.espn.com.ar/futbol/" if sport == "futbol" else "https://www.espn.com.ar/basquetbol/"
    status, html = await _fetch_html(url)
    if status is None:
        return [], [], "network_error"
    if status >= 400:
        return [], [], f"http_{status}"
    fixtures = _extract_fixtures_from_tables(html, sport, COMPETITION_MAP[sport][slug]["label"], "espn")
    standings = _extract_standings_from_tables(html, sport)
    return standings, fixtures, None


async def _try_laliganacional_oficial(slug: str) -> tuple[list[dict], list[dict], str | None]:
    urls = []
    if slug == "liga-nacional":
        urls = [
            "https://www.laliganacional.com.ar/laliga/fixture",
            "https://www.laliganacional.com.ar/laliga/tabla-posiciones",
        ]
    elif slug == "liga-argentina":
        urls = [
            "https://www.laliganacional.com.ar/laligaargentina/fixture",
            "https://www.laliganacional.com.ar/laligaargentina/",
        ]
    elif slug == "liga-federal":
        urls = [
            "https://www.laliganacional.com.ar/",
        ]

    all_html = ""
    last_status = None
    for u in urls:
        st, html = await _fetch_html(u)
        last_status = st
        if st and st < 400 and html:
            all_html += "\n" + html

    if not all_html:
        return [], [], f"http_{last_status}" if last_status else "network_error"

    fixtures = _extract_fixtures_from_tables(all_html, "basquet", COMPETITION_MAP["basquet"][slug]["label"], "laliganacional_oficial")
    standings = _extract_standings_from_tables(all_html, "basquet")
    return standings, fixtures, None


# ─────────────────────────────────────────────────────────────────────────────
# CHAINS REALES
# ─────────────────────────────────────────────────────────────────────────────

async def _run_football_chain(slug: str, attempted: list[dict]) -> tuple[list[dict], list[dict], str | None, str | None]:
    """
    Devuelve standings, fixtures, source_used, error_detail
    """
    # 1) API-Football (si hay key)
    key = (os.getenv("API_FOOTBALL_KEY", "") or "").strip()
    if _is_placeholder_key(key):
        attempted.append(_make_attempt("api_football", False, "API_FOOTBALL_KEY missing"))
    else:
        try:
            raw = await get_football_overview(slug)
            standings, fixtures = _normalize_from_service_payload("futbol", slug, raw, "api_football")
            attempted.append(_make_attempt("api_football", bool(standings or fixtures), raw.get("error")))
            logger.info("football source=api_football slug=%s standings=%s fixtures=%s", slug, len(standings), len(fixtures))
            if standings or fixtures:
                return standings, fixtures, "api_football", None
        except Exception as e:
            attempted.append(_make_attempt("api_football", False, str(e)))
            logger.exception("football source=api_football slug=%s exception", slug)

    # 2) LPF oficial SOLO para liga profesional
    if slug in {"liga-profesional-argentina"}:
        try:
            standings, fixtures, err = await _try_lpf_oficial(slug)
            attempted.append(_make_attempt("lpf_oficial", bool(standings or fixtures), err))
            logger.info("football source=lpf_oficial slug=%s standings=%s fixtures=%s err=%s", slug, len(standings), len(fixtures), err)
            if standings or fixtures:
                return standings, fixtures, "lpf_oficial", None
        except Exception as e:
            attempted.append(_make_attempt("lpf_oficial", False, str(e)))
            logger.exception("football source=lpf_oficial slug=%s exception", slug)

    # 3) ESPN
    try:
        standings, fixtures, err = await _try_espn_generic(slug, "futbol")
        attempted.append(_make_attempt("espn", bool(standings or fixtures), err))
        logger.info("football source=espn slug=%s standings=%s fixtures=%s err=%s", slug, len(standings), len(fixtures), err)
        if standings or fixtures:
            return standings, fixtures, "espn", None
    except Exception as e:
        attempted.append(_make_attempt("espn", False, str(e)))
        logger.exception("football source=espn slug=%s exception", slug)

    # 4) Promiedos
    try:
        standings, fixtures, err = await _try_promiedos(slug, "futbol")
        attempted.append(_make_attempt("promiedos", bool(standings or fixtures), err))
        logger.info("football source=promiedos slug=%s standings=%s fixtures=%s err=%s", slug, len(standings), len(fixtures), err)
        if standings or fixtures:
            return standings, fixtures, "promiedos", None
    except Exception as e:
        attempted.append(_make_attempt("promiedos", False, str(e)))
        logger.exception("football source=promiedos slug=%s exception", slug)

    return [], [], None, "sin_datos_en_todas_las_fuentes"


async def _run_basket_chain(slug: str, attempted: list[dict]) -> tuple[list[dict], list[dict], str | None, str | None]:
    # 1) Oficial Liga Nacional / Liga Argentina (site laliganacional)
    try:
        standings, fixtures, err = await _try_laliganacional_oficial(slug)
        attempted.append(_make_attempt("laliganacional_oficial", bool(standings or fixtures), err))
        logger.info("basket source=laliganacional_oficial slug=%s standings=%s fixtures=%s err=%s", slug, len(standings), len(fixtures), err)
        if standings or fixtures:
            return standings, fixtures, "laliganacional_oficial", None
    except Exception as e:
        attempted.append(_make_attempt("laliganacional_oficial", False, str(e)))
        logger.exception("basket source=laliganacional_oficial slug=%s exception", slug)

    # 2) Quinto Cuarto (vía parser genérico html)
    try:
        st, html = await _fetch_html("https://quintocuartonea.com/")
        if st is None:
            attempted.append(_make_attempt("quintocuarto", False, "network_error"))
        elif st >= 400:
            attempted.append(_make_attempt("quintocuarto", False, f"http_{st}", st))
        else:
            fixtures = _extract_fixtures_from_tables(html, "basquet", COMPETITION_MAP["basquet"][slug]["label"], "quintocuarto")
            standings = _extract_standings_from_tables(html, "basquet")
            attempted.append(_make_attempt("quintocuarto", bool(standings or fixtures)))
            logger.info("basket source=quintocuarto slug=%s standings=%s fixtures=%s", slug, len(standings), len(fixtures))
            if standings or fixtures:
                return standings, fixtures, "quintocuarto", None
    except Exception as e:
        attempted.append(_make_attempt("quintocuarto", False, str(e)))
        logger.exception("basket source=quintocuarto slug=%s exception", slug)

    # 3) get_lnb_overview como fallback de servicio ya existente
    try:
        raw = await get_lnb_overview(slug)
        standings, fixtures = _normalize_from_service_payload("basquet", slug, raw, "lnb_service")
        attempted.append(_make_attempt("lnb_service", bool(standings or fixtures), raw.get("error")))
        logger.info("basket source=lnb_service slug=%s standings=%s fixtures=%s", slug, len(standings), len(fixtures))
        if standings or fixtures:
            return standings, fixtures, "lnb_service", None
    except Exception as e:
        attempted.append(_make_attempt("lnb_service", False, str(e)))
        logger.exception("basket source=lnb_service slug=%s exception", slug)

    return [], [], None, "sin_datos_en_todas_las_fuentes"


# ─────────────────────────────────────────────────────────────────────────────
# API SERVICE
# ─────────────────────────────────────────────────────────────────────────────

async def list_competitions(sport: str) -> dict:
    return {
        "sport": sport,
        "items": [{"slug": k, "label": v["label"]} for k, v in COMPETITION_MAP.get(sport, {}).items()],
    }


async def get_competition_overview(sport: str, slug: str) -> dict:
    input_slug = slug
    slug = resolve_competition_slug(sport, slug)
    competition_label = COMPETITION_MAP.get(sport, {}).get(slug, {}).get("label", slug)

    logger.info("competition_overview start sport=%s input_slug=%s normalized_slug=%s", sport, input_slug, slug)

    attempted: list[dict] = []
    standings: list[dict] = []
    fixtures: list[dict] = []
    source_used: str | None = None
    final_error: str | None = None

    if sport not in COMPETITION_MAP or slug not in COMPETITION_MAP[sport]:
        return _empty_payload(sport, competition_label, attempted, "competencia_no_soportada")

    if sport == "futbol":
        standings, fixtures, source_used, final_error = await _run_football_chain(slug, attempted)
    elif sport == "basquet":
        standings, fixtures, source_used, final_error = await _run_basket_chain(slug, attempted)
    else:
        final_error = "deporte_no_soportado"

    # si alguna fuente funcionó, error null
    if standings or fixtures:
        final_error = None

    logger.info(
        "competition_overview end sport=%s slug=%s source_used=%s fixtures=%s standings=%s error=%s",
        sport, slug, source_used, len(fixtures), len(standings), final_error
    )

    return {
        "sport": sport,
        "competition": competition_label,
        "season": datetime.now().year,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source_used": source_used,
        "sources_attempted": attempted,  # ejecutadas de verdad
        "standings": standings,
        "fixtures": fixtures,
        "groups": [],
        "error": final_error or ("sin_datos_en_todas_las_fuentes" if (not standings and not fixtures) else None),
    }


async def get_competition_fixture(sport: str, slug: str) -> dict:
    data = await get_competition_overview(sport, slug)
    return {
        "sport": data["sport"],
        "competition": data["competition"],
        "season": data["season"],
        "updated_at": data["updated_at"],
        "source_used": data["source_used"],
        "sources_attempted": data["sources_attempted"],
        "fixtures": data["fixtures"],
        "error": data["error"],
    }


async def get_competition_table(sport: str, slug: str) -> dict:
    data = await get_competition_overview(sport, slug)
    return {
        "sport": data["sport"],
        "competition": data["competition"],
        "season": data["season"],
        "updated_at": data["updated_at"],
        "source_used": data["source_used"],
        "sources_attempted": data["sources_attempted"],
        "standings": data["standings"],
        "error": data["error"],
    }


async def get_competition_scorers(sport: str, slug: str) -> dict:
    return {
        "sport": sport,
        "slug": slug,
        "rows": [],
        "error": None,
    }
