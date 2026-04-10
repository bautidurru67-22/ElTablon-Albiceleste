"""
Adapter de rugby argentino.
Fuente primaria : UAR (uar.com.ar)
Fallback        : Sofascore
"""
import logging
import re
from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch
from scraping.sources import sofascore, uar as uar_source
from scraping.normalizers import sofascore_normalizer
from scraping.argentina import detect_argentina_relevance

logger = logging.getLogger(__name__)


class RugbyAdapter(BaseScraper):
    """
    Rugby argentino:
      - Los Pumas (The Rugby Championship, giras)
      - Pumitas / Argentina 7s
      - SuperRugby Américas / Jaguares
      - URBA Top 14
    """
    EXTRA_HEADERS = {"Referer": "https://www.uar.com.ar/"}

    async def scrape(self) -> list[NormalizedMatch]:
        matches: list[NormalizedMatch] = []

        # Fuente 1: UAR — fixture y resultados oficiales
        try:
            html = await self.fetch_html(uar_source.FIXTURES_URL)
            raws = uar_source.parse_matches(html)
            local = [self._normalize_raw(r) for r in raws]
            local = [m for m in local if m is not None]
            logger.info(f"[rugby/uar] {len(local)} partidos")
            matches.extend(local)
        except Exception as e:
            logger.warning(f"[rugby/uar] falló: {e}")

        # Fallback: Sofascore — internacionales + en vivo
        try:
            data = await sofascore.get_events_by_date("rugby")
            events = data.get("events", [])
            ss = sofascore_normalizer.normalize_events(events, "rugby")
            existing = {m.id for m in matches}
            new = [m for m in ss if m.id not in existing]
            logger.info(f"[rugby/sofascore-fallback] {len(new)} adicionales")
            matches.extend(new)
        except Exception as e:
            logger.warning(f"[rugby/sofascore] falló: {e}")

        # En vivo
        try:
            data = await sofascore.get_live_events("rugby")
            events = data.get("events", [])
            live = sofascore_normalizer.normalize_events(events, "rugby")
            existing = {m.id for m in matches}
            new_live = [m for m in live if m.id not in existing]
            logger.info(f"[rugby/sofascore-live] {len(new_live)} en vivo")
            matches.extend(new_live)
        except Exception as e:
            logger.warning(f"[rugby/sofascore-live] falló: {e}")

        return matches

    def _normalize_raw(self, raw: dict) -> NormalizedMatch | None:
        try:
            home = raw.get("home", "").strip()
            away = raw.get("away", "").strip()
            if not home or not away:
                return None
            competition = raw.get("competition", "Rugby Argentina")
            relevance, arg_team = detect_argentina_relevance(home, away, competition, "rugby")
            if relevance == "none":
                return None
            home_slug = re.sub(r"\W+", "-", home.lower())[:20]
            away_slug = re.sub(r"\W+", "-", away.lower())[:20]
            return NormalizedMatch(
                id=f"rugby-uar-{home_slug}-{away_slug}",
                sport="rugby",
                source="uar",
                competition=competition,
                home_team=home,
                away_team=away,
                home_score=raw.get("home_score"),
                away_score=raw.get("away_score"),
                status=raw.get("status", "upcoming"),
                start_time_arg=raw.get("start_time"),
                argentina_relevance=relevance,
                argentina_team=arg_team,
                raw=raw,
            )
        except Exception:
            return None
