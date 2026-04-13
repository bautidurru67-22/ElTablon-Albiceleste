"""
Fútbol argentino.

Fuentes en orden de prioridad:
1. ESPN API pública  — Liga Prof, Libertadores, Sudamericana, Copa Arg, ligas europeas
2. API-Football v3   — si API_FOOTBALL_KEY está configurado en Railway
3. TheSportsDB       — next/past events como complemento
4. Sofascore         — fallback si todo lo anterior falla

ESPN no requiere key y no bloquea IPs de Railway.
"""
import logging
import re
from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch
from scraping.argentina import detect_argentina_relevance, normalize_str
from scraping.sources.espn_api import get_sport_events, parse_event as parse_espn
from scraping.sources.apifootball_free import get_fixtures_today, get_live_fixtures, parse_fixture as parse_apifb
from scraping.sources.thesportsdb import get_events_today, get_next_events, get_last_events, parse_event as parse_tsdb
from scraping.sources.sofascore_safe import get_events_by_date as ss_today, get_live_events as ss_live
from scraping.normalizers import sofascore_normalizer

logger = logging.getLogger(__name__)

# IDs TheSportsDB para fútbol argentino
TSDB_FOOTBALL = {
    4406: "Liga Profesional Argentina",
    4500: "Copa Libertadores",
}


def _make(raw: dict, source: str) -> NormalizedMatch | None:
    home = raw.get("home", "").strip()
    away = raw.get("away", "").strip()
    if not home or not away:
        return None
    comp = raw.get("competition", "") or ""
    rel, arg_team = detect_argentina_relevance(home, away, comp, "futbol")
    if rel == "none":
        return None
    hn = re.sub(r"\W+", "-", normalize_str(home))[:20]
    an = re.sub(r"\W+", "-", normalize_str(away))[:20]
    return NormalizedMatch(
        id=f"futbol-{source}-{hn}-{an}",
        sport="futbol", source=source,
        competition=comp or "Fútbol",
        home_team=home, away_team=away,
        home_score=raw.get("home_score"),
        away_score=raw.get("away_score"),
        status=raw.get("status", "upcoming"),
        minute=raw.get("minute"),
        start_time_arg=raw.get("start_time"),
        argentina_relevance=rel,
        argentina_team=arg_team,
        broadcast=raw.get("broadcast"),
        raw=raw,
    )


class FootballAdapter(BaseScraper):

    async def scrape(self) -> list[NormalizedMatch]:
        matches: list[NormalizedMatch] = []
        seen: set[str] = set()

        def add(m: NormalizedMatch | None) -> None:
            if m and m.id not in seen:
                seen.add(m.id)
                matches.append(m)

        # ── 1. ESPN API (no key, no bloqueo en Railway) ───────────────────
        try:
            events = await get_sport_events("futbol")
            before = len(matches)
            for ev in events:
                raw = parse_espn(ev)
                if raw:
                    add(_make(raw, "espn"))
            logger.info(f"[football/espn] {len(matches) - before} de {len(events)} eventos")
        except Exception as e:
            logger.warning(f"[football/espn] {e}")

        # ── 2. API-Football (si hay key en Railway env vars) ───────────────
        try:
            fixtures = await get_fixtures_today()
            live_fix = await get_live_fixtures()
            before = len(matches)
            for fix in fixtures + live_fix:
                raw = parse_apifb(fix)
                add(_make(raw, "apifb"))
            if fixtures or live_fix:
                logger.info(f"[football/api_football] {len(matches) - before}")
        except Exception as e:
            logger.warning(f"[football/api_football] {e}")

        # ── 3. TheSportsDB (complemento) ───────────────────────────────────
        try:
            before = len(matches)
            for lid, lname in TSDB_FOOTBALL.items():
                for fn in [get_events_today, get_next_events, get_last_events]:
                    for ev in await fn(lid):
                        raw = parse_tsdb(ev, "futbol")
                        raw["competition"] = raw.get("competition") or lname
                        add(_make(raw, "tsdb"))
            logger.info(f"[football/tsdb] {len(matches) - before}")
        except Exception as e:
            logger.warning(f"[football/tsdb] {e}")

        # ── 4. Sofascore (fallback — puede dar 403 en Railway) ─────────────
        if not matches:
            try:
                before = len(matches)
                for fn in [ss_today, ss_live]:
                    data = await fn("futbol")
                    for m in sofascore_normalizer.normalize_events(
                            data.get("events", []), "futbol"):
                        if m.id not in seen:
                            seen.add(m.id); matches.append(m)
                logger.info(f"[football/sofascore] {len(matches) - before}")
            except Exception as e:
                logger.warning(f"[football/sofascore] {e}")

        logger.info(f"[football] TOTAL {len(matches)}")
        return matches
