"""
Fútbol argentino.

Fuentes en orden:
1. API-Football v3 (api-football.com) — oficial, gratis 100 req/día, requiere key
2. TheSportsDB          — gratuita sin key, liga profesional + libertadores
3. Sofascore            — fallback, puede fallar en Railway (403 Cloudflare)
"""
import logging
import re
from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch
from scraping.argentina import detect_argentina_relevance, normalize_str
from scraping.sources.apifootball_free import get_fixtures_today, get_live_fixtures, parse_fixture as parse_apifb
from scraping.sources.thesportsdb import get_events_today, parse_event, LEAGUE_IDS as TSDB_LEAGUES
from scraping.sources.sofascore_safe import get_events_by_date as ss_today, get_live_events as ss_live
from scraping.normalizers import sofascore_normalizer

logger = logging.getLogger(__name__)

# Ligas TheSportsDB relevantes para Argentina
TSDB_FOOTBALL_LEAGUES = {
    4406: "Liga Profesional Argentina",
    4500: "Copa Libertadores",
    4501: "Copa Sudamericana",
}


def _make_match(raw: dict, source_id: str) -> NormalizedMatch | None:
    home = raw.get("home", "").strip()
    away = raw.get("away", "").strip()
    if not home or not away:
        return None
    comp = raw.get("competition", "") or ""
    relevance, arg_team = detect_argentina_relevance(home, away, comp, "futbol")
    if relevance == "none":
        return None
    h_n = re.sub(r"\W+", "-", normalize_str(home))[:20]
    a_n = re.sub(r"\W+", "-", normalize_str(away))[:20]
    return NormalizedMatch(
        id=f"futbol-{source_id}-{h_n}-{a_n}",
        sport="futbol",
        source=source_id,
        competition=comp or "Fútbol",
        home_team=home,
        away_team=away,
        home_score=raw.get("home_score"),
        away_score=raw.get("away_score"),
        status=raw.get("status", "upcoming"),
        minute=raw.get("minute"),
        start_time_arg=raw.get("start_time"),
        argentina_relevance=relevance,
        argentina_team=arg_team,
        raw=raw,
    )


class FootballAdapter(BaseScraper):

    async def scrape(self) -> list[NormalizedMatch]:
        matches: list[NormalizedMatch] = []
        seen: set[str] = set()

        def _add(m: NormalizedMatch | None) -> None:
            if m and m.id not in seen:
                seen.add(m.id)
                matches.append(m)

        # ── 1. API-Football (oficial, requiere API_FOOTBALL_KEY) ───────────
        try:
            fixtures = await get_fixtures_today()
            live_fix = await get_live_fixtures()
            for fix in fixtures + live_fix:
                raw = parse_apifb(fix)
                _add(_make_match(raw, "apifb"))
            logger.info(f"[football/api_football] {len([m for m in matches if m.source=='apifb'])} partidos")
        except Exception as e:
            logger.warning(f"[football/api_football] {e}")

        # ── 2. TheSportsDB (gratuita sin key) ─────────────────────────────
        try:
            before = len(matches)
            for league_id, league_name in TSDB_FOOTBALL_LEAGUES.items():
                events = await get_events_today(league_id)
                for ev in events:
                    raw = parse_event(ev, "futbol")
                    raw["competition"] = raw.get("competition") or league_name
                    _add(_make_match(raw, "tsdb"))
            logger.info(f"[football/thesportsdb] {len(matches) - before} partidos")
        except Exception as e:
            logger.warning(f"[football/thesportsdb] {e}")

        # ── 3. Sofascore (fallback — puede fallar con 403 en Railway) ─────
        try:
            before = len(matches)
            for fn, label in [(ss_today, "sched"), (ss_live, "live")]:
                data = await fn("futbol")
                events = data.get("events", [])
                ss = sofascore_normalizer.normalize_events(events, "futbol")
                for m in ss:
                    if m.id not in seen:
                        seen.add(m.id)
                        matches.append(m)
            logger.info(f"[football/sofascore] {len(matches) - before} adicionales")
        except Exception as e:
            logger.warning(f"[football/sofascore] {e}")

        logger.info(f"[football] TOTAL {len(matches)}")
        return matches
