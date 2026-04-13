"""
Fútbol argentino robusto (sin mocks).
Estrategia:
1) Promiedos
2) AFA
3) API-Football (si hay API_FOOTBALL_KEY)
4) Sofascore (today + live)

Siempre intenta TODAS las fuentes (no corta en la primera),
deduplica por hash de equipos, y expone diagnóstico por fuente.
"""
import logging
import re
from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch
from scraping.argentina import detect_argentina_relevance, normalize_str

from scraping.sources.promiedos import get_today_html, parse_matches
from scraping.sources.afa import get_fixture_html, parse_fixture
from scraping.normalizers.promiedos_normalizer import normalize_matches as normalize_promiedos

from scraping.sources.api_football import get_fixtures_today, parse_fixture as parse_apifootball
from scraping.sources.sofascore import get_events_by_date, get_live_events
from scraping.normalizers import sofascore_normalizer

logger = logging.getLogger(__name__)


def _slug(s: str) -> str:
    s = normalize_str(s or "")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:40] if s else "x"


class FootballAdapter(BaseScraper):
    SOURCE_ORDER = ["promiedos", "afa", "api_football", "sofascore"]
    DIAG_VERSION = "football-diag-v4-2026-04-13"
    LAST_RUN: dict = {}

    async def scrape(self) -> list[NormalizedMatch]:
        matches: list[NormalizedMatch] = []
        seen: set[str] = set()
        diagnostics: dict = {
            "diag_version": self.DIAG_VERSION,
            "sources": {},
            "total_unique": 0,
        }

        def stable_id(m: NormalizedMatch) -> str:
            # ID estable por equipos + competencia + source para evitar duplicados cruzados
            return f"futbol-{m.source}-{_slug(m.competition)}-{_slug(m.home_team)}-{_slug(m.away_team)}"

        def add(m: NormalizedMatch | None) -> None:
            if not m:
                return
            if m.argentina_relevance == "none":
                return
            sid = stable_id(m)
            if sid in seen:
                return
            seen.add(sid)
            m.id = sid
            matches.append(m)

        def record(source: str, raw_count: int = 0, added_count: int = 0, error: str | None = None):
            diagnostics["sources"][source] = {
                "raw_count": raw_count,
                "added_count": added_count,
                "error": error,
            }

        # 1) PROMIEDOS
        try:
            html = await get_today_html()
            raw = parse_matches(html)
            before = len(matches)
            for m in normalize_promiedos(raw):
                add(m)
            added = len(matches) - before
            record("promiedos", raw_count=len(raw), added_count=added)
            logger.info(f"[football/promiedos] raw={len(raw)} added={added}")
        except Exception as e:
            record("promiedos", error=str(e))
            logger.warning(f"[football/promiedos] {e}")

        # 2) AFA
        try:
            html = await get_fixture_html()
            raw = parse_fixture(html or "")
            before = len(matches)
            for m in normalize_promiedos(raw):
                add(m)
            added = len(matches) - before
            record("afa", raw_count=len(raw), added_count=added)
            logger.info(f"[football/afa] raw={len(raw)} added={added}")
        except Exception as e:
            record("afa", error=str(e))
            logger.warning(f"[football/afa] {e}")

        # 3) API-FOOTBALL (requiere API_FOOTBALL_KEY)
        try:
            fixtures = await get_fixtures_today()
            before = len(matches)
            for fx in fixtures:
                raw = parse_apifootball(fx)
                home = raw.get("home", "")
                away = raw.get("away", "")
                comp = raw.get("competition", "")
                rel, arg_team = detect_argentina_relevance(home, away, comp, "futbol")
                if rel == "none":
                    continue

                m = NormalizedMatch(
                    id="tmp",
                    sport="futbol",
                    source="api_football",
                    competition=comp or "Fútbol",
                    home_team=home,
                    away_team=away,
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
                add(m)

            added = len(matches) - before
            record("api_football", raw_count=len(fixtures), added_count=added)
            logger.info(f"[football/api_football] raw={len(fixtures)} added={added}")
        except Exception as e:
            record("api_football", error=str(e))
            logger.warning(f"[football/api_football] {e}")

        # 4) SOFASCORE (today + live)
        try:
            before = len(matches)
            raw_total = 0

            for fn in (get_events_by_date, get_live_events):
                data = await fn("futbol")
                events = data.get("events", [])
                raw_total += len(events)
                for m in sofascore_normalizer.normalize_events(events, "futbol"):
                    add(m)

            added = len(matches) - before
            record("sofascore", raw_count=raw_total, added_count=added)
            logger.info(f"[football/sofascore] raw={raw_total} added={added}")
        except Exception as e:
            record("sofascore", error=str(e))
            logger.warning(f"[football/sofascore] {e}")

        diagnostics["total_unique"] = len(matches)
        FootballAdapter.LAST_RUN = diagnostics
        logger.info(f"[football] TOTAL={len(matches)}")
        return matches
