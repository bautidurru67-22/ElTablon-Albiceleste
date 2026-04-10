"""
Adapter de básquet argentino.
Fuente primaria : LNB (lnb.com.ar) + CABB (cabb.com.ar)
Fallback        : Sofascore
"""
import logging
import re
from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch
from scraping.sources import sofascore
from scraping.sources import lnb as lnb_source
from scraping.normalizers import sofascore_normalizer
from scraping.argentina import detect_argentina_relevance

logger = logging.getLogger(__name__)

CABB_URL = "https://cabb.com.ar/competencias"


class BasketballAdapter(BaseScraper):
    """
    Básquet argentino:
      - Liga Nacional (lnb.com.ar) — fuente primaria
      - CABB selecciones (cabb.com.ar) — fuente primaria
      - NBA / ACB con ARG — Sofascore fallback
    """
    async def scrape(self) -> list[NormalizedMatch]:
        matches: list[NormalizedMatch] = []

        # Fuente 1: LNB — Liga Nacional
        try:
            html = await self.fetch_html(lnb_source.FIXTURES_URL)
            raws = lnb_source.parse_matches(html)
            local = [self._normalize_raw(r) for r in raws]
            local = [m for m in local if m is not None]
            logger.info(f"[basketball/lnb] {len(local)} partidos")
            matches.extend(local)
        except Exception as e:
            logger.warning(f"[basketball/lnb] falló: {e}")

        # Fuente 2: CABB — selección argentina
        try:
            html = await self.fetch_html(CABB_URL)
            raws = lnb_source.parse_matches(html)   # misma estructura HTML aproximada
            cabb = [self._normalize_raw(r, competition_override="Selección Argentina") for r in raws]
            cabb = [m for m in cabb if m is not None]
            existing = {m.id for m in matches}
            new = [m for m in cabb if m.id not in existing]
            logger.info(f"[basketball/cabb] {len(new)} partidos selección")
            matches.extend(new)
        except Exception as e:
            logger.warning(f"[basketball/cabb] falló: {e}")

        # Fallback: Sofascore — NBA / ACB / internacionales con ARG
        try:
            data = await sofascore.get_events_by_date("basquet")
            events = data.get("events", [])
            ss = sofascore_normalizer.normalize_events(events, "basquet")
            existing = {m.id for m in matches}
            new = [m for m in ss if m.id not in existing]
            logger.info(f"[basketball/sofascore-fallback] {len(new)} adicionales")
            matches.extend(new)
        except Exception as e:
            logger.warning(f"[basketball/sofascore] falló: {e}")

        # En vivo Sofascore
        try:
            data = await sofascore.get_live_events("basquet")
            events = data.get("events", [])
            live = sofascore_normalizer.normalize_events(events, "basquet")
            existing = {m.id for m in matches}
            new_live = [m for m in live if m.id not in existing]
            logger.info(f"[basketball/sofascore-live] {len(new_live)} en vivo")
            matches.extend(new_live)
        except Exception as e:
            logger.warning(f"[basketball/sofascore-live] falló: {e}")

        return matches

    def _normalize_raw(self, raw: dict, competition_override: str | None = None) -> NormalizedMatch | None:
        try:
            home = raw.get("home", "").strip()
            away = raw.get("away", "").strip()
            if not home or not away:
                return None
            competition = competition_override or raw.get("competition", "Liga Nacional")
            relevance, arg_team = detect_argentina_relevance(home, away, competition, "basquet")
            if relevance == "none":
                return None
            home_slug = re.sub(r"\W+", "-", home.lower())[:20]
            away_slug = re.sub(r"\W+", "-", away.lower())[:20]
            return NormalizedMatch(
                id=f"basquet-{raw.get('source','lnb')}-{home_slug}-{away_slug}",
                sport="basquet",
                source=raw.get("source", "lnb"),
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
