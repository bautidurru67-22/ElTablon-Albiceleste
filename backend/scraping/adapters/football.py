"""
Fútbol argentino (sin mocks).
Prioridad de fuentes:
1) Promiedos (local ARG)
2) AFA (oficial local)
3) Sofascore (fallback)
"""
import logging
from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch
from scraping.sources.promiedos import get_today_html, parse_matches
from scraping.sources.afa import get_fixture_html, parse_fixture
from scraping.normalizers.promiedos_normalizer import normalize_matches as normalize_promiedos
from scraping.sources.sofascore import get_events_by_date, get_live_events
from scraping.normalizers import sofascore_normalizer

logger = logging.getLogger(__name__)


class FootballAdapter(BaseScraper):
    SOURCE_ORDER = ["promiedos", "afa", "sofascore"]

    async def scrape(self) -> list[NormalizedMatch]:
        matches: list[NormalizedMatch] = []
        seen: set[str] = set()

        def add(m: NormalizedMatch | None):
            if m and m.id not in seen:
                seen.add(m.id)
                matches.append(m)

        # 1) Promiedos: fuerte para Liga Profesional / Argentina
        try:
            html = await get_today_html()
            raw = parse_matches(html)
            before = len(matches)
            for m in normalize_promiedos(raw):
                add(m)
            logger.info(f"[football/promiedos] +{len(matches) - before} ({len(raw)} raw)")
        except Exception as e:
            logger.warning(f"[football/promiedos] {e}")

        # 2) AFA oficial (fallback 1)
        if not matches:
            try:
                html = await get_fixture_html()
                raw = parse_fixture(html or "")
                before = len(matches)
                for m in normalize_promiedos(raw):
                    add(m)
                logger.info(f"[football/afa] +{len(matches) - before} ({len(raw)} raw)")
            except Exception as e:
                logger.warning(f"[football/afa] {e}")

        # 3) Sofascore fallback para no quedar vacío
        if not matches:
            try:
                before = len(matches)
                for fn in [get_events_by_date, get_live_events]:
                    data = await fn("futbol")
                    for m in sofascore_normalizer.normalize_events(data.get("events", []), "futbol"):
                        add(m)
                logger.info(f"[football/sofascore] +{len(matches) - before}")
            except Exception as e:
                logger.warning(f"[football/sofascore] {e}")

        logger.info(f"[football] TOTAL={len(matches)}")
        return matches
