"""
Adapter fútbol argentino.

Jerarquía de fuentes (de mayor a menor prioridad):
1. Promiedos.com.ar    — Liga Profesional, torneos locales (HTML, muy fiable)
2. API-Football        — si API_FOOTBALL_KEY está configurado (oficial, gratis 100/día)
3. Sofascore scheduled — Libertadores, Sudamericana, ligas europeas con ARG
4. Sofascore live      — partidos en vivo
5. Flashscore         — como cobertura adicional
"""
import logging
from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch
from scraping.sources import promiedos, sofascore
from scraping.sources.api_football import get_fixtures_today, parse_fixture as parse_api_fixture
from scraping.sources.flashscore import get_argentina_page, parse_matches_html
from scraping.normalizers import promiedos_normalizer, sofascore_normalizer
from scraping.argentina import detect_argentina_relevance, normalize_str
import re

logger = logging.getLogger(__name__)


class FootballAdapter(BaseScraper):
    EXTRA_HEADERS = {"Referer": "https://www.promiedos.com.ar/"}

    async def scrape(self) -> list[NormalizedMatch]:
        matches: list[NormalizedMatch] = []

        # ── 1. Promiedos — Liga Profesional y torneos locales ──────────────
        try:
            html = await promiedos.get_today_html()
            raws = promiedos.parse_matches(html)
            local = promiedos_normalizer.normalize_matches(raws)
            logger.info(f"[football/promiedos] {len(local)}")
            matches.extend(local)
        except Exception as e:
            logger.warning(f"[football/promiedos] {e}")

        # ── 2. API-Football — si hay key configurada ────────────────────────
        try:
            fixtures = await get_fixtures_today()
            existing = {m.id for m in matches}
            for fix in fixtures:
                raw = parse_api_fixture(fix)
                home = raw.get("home", "")
                away = raw.get("away", "")
                if not home or not away:
                    continue
                relevance, arg_team = detect_argentina_relevance(home, away, raw.get("competition", ""), "futbol")
                if relevance == "none":
                    continue
                h_n = re.sub(r"\W+", "-", normalize_str(home))[:20]
                a_n = re.sub(r"\W+", "-", normalize_str(away))[:20]
                mid = f"futbol-apifb-{h_n}-{a_n}"
                if mid not in existing:
                    existing.add(mid)
                    matches.append(NormalizedMatch(
                        id=mid, sport="futbol", source="api_football",
                        competition=raw.get("competition", "Fútbol Argentina"),
                        home_team=home, away_team=away,
                        home_score=raw.get("home_score"),
                        away_score=raw.get("away_score"),
                        status=raw.get("status", "upcoming"),
                        minute=raw.get("minute"),
                        start_time_arg=raw.get("start_time"),
                        argentina_relevance=relevance,
                        argentina_team=arg_team, raw=raw,
                    ))
            if fixtures:
                logger.info(f"[football/api_football] {len(fixtures)} fixtures procesados")
        except Exception as e:
            logger.warning(f"[football/api_football] {e}")

        # ── 3. Sofascore scheduled — Libertadores, Sudamericana, exterior ──
        try:
            data = await sofascore.get_events_by_date("futbol")
            events = data.get("events", [])
            ss = sofascore_normalizer.normalize_events(events, "futbol")
            existing = {m.id for m in matches}
            new = [m for m in ss if m.id not in existing]
            logger.info(f"[football/ss-sched] {len(new)} adicionales")
            matches.extend(new)
        except Exception as e:
            logger.warning(f"[football/ss-sched] {e}")

        # ── 4. Sofascore live ───────────────────────────────────────────────
        try:
            data = await sofascore.get_live_events("futbol")
            events = data.get("events", [])
            live = sofascore_normalizer.normalize_events(events, "futbol")
            existing = {m.id for m in matches}
            new_live = [m for m in live if m.id not in existing]
            logger.info(f"[football/ss-live] {len(new_live)} en vivo")
            matches.extend(new_live)
        except Exception as e:
            logger.warning(f"[football/ss-live] {e}")

        # ── 5. Flashscore — cobertura adicional ───────────────────────────
        try:
            html_fs = await get_argentina_page("futbol")
            if html_fs:
                raws_fs = parse_matches_html(html_fs, "futbol")
                existing = {m.id for m in matches}
                for raw in raws_fs:
                    home = raw.get("home", "")
                    away = raw.get("away", "")
                    if not home or not away:
                        continue
                    relevance, arg_team = detect_argentina_relevance(home, away, raw.get("competition", ""), "futbol")
                    if relevance == "none":
                        continue
                    h_n = re.sub(r"\W+", "-", normalize_str(home))[:20]
                    a_n = re.sub(r"\W+", "-", normalize_str(away))[:20]
                    mid = f"futbol-fs-{h_n}-{a_n}"
                    if mid not in existing:
                        existing.add(mid)
                        matches.append(NormalizedMatch(
                            id=mid, sport="futbol", source="flashscore",
                            competition=raw.get("competition", "Argentina"),
                            home_team=home, away_team=away,
                            home_score=raw.get("home_score"),
                            away_score=raw.get("away_score"),
                            status=raw.get("status", "upcoming"),
                            minute=raw.get("minute"),
                            start_time_arg=raw.get("start_time"),
                            argentina_relevance=relevance,
                            argentina_team=arg_team, raw=raw,
                        ))
        except Exception as e:
            logger.warning(f"[football/flashscore] {e}")

        logger.info(f"[football] TOTAL {len(matches)}")
        return matches
