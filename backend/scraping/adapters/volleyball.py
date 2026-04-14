"""
Adapter vóley.
1. Sofascore (primary para internacionales)
2. voley.org.ar — liga argentina
3. fivb.com — selección argentina
"""
import logging
import re
from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch
from scraping.sources import sofascore
from scraping.normalizers import sofascore_normalizer
from scraping.argentina import detect_argentina_relevance, normalize_str

logger = logging.getLogger(__name__)

VOLEY_ARG_URL = "https://www.voley.org.ar/competencias"
FIVB_URL = "https://www.fivb.com/en/volleyball/competitions"


class VolleyballAdapter(BaseScraper):
    SOURCE_ORDER = ["sofascore_scheduled", "sofascore_live", "voley.org.ar"]
    DIAG_VERSION = "volleyball-diag-v1-2026-04-14"
    LAST_RUN: dict = {}
    async def scrape(self) -> list[NormalizedMatch]:
        matches = []

        for fn, label in [
            (lambda: sofascore.get_events_by_date("voley"), "scheduled"),
            (lambda: sofascore.get_live_events("voley"), "live"),
        ]:
            try:
                data = await fn()
                events = data.get("events", [])
                ss = sofascore_normalizer.normalize_events(events, "voley")
                if not ss:
                    ss = sofascore_normalizer.normalize_events_all(events, "voley")
                existing = {m.id for m in matches}
                new = [m for m in ss if m.id not in existing]
                logger.info(f"[volleyball/ss-{label}] {len(new)}")
                matches.extend(new)
            except Exception as e:
                logger.warning(f"[volleyball/ss-{label}] {e}")

        # voley.org.ar fallback
        if not matches:
            try:
                html = await self.fetch_html(VOLEY_ARG_URL)
                local = self._parse_voley_ar(html)
                logger.info(f"[volleyball/voley.org.ar] {len(local)}")
                matches.extend(local)
            except Exception as e:
                logger.warning(f"[volleyball/voley.org.ar] {e}")

        logger.info(f"[volleyball] TOTAL {len(matches)}")
        return matches

    def _parse_voley_ar(self, html: str) -> list[NormalizedMatch]:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        results = []
        comp = "Liga de Voleibol Argentina"
        for row in soup.select("div.partido, div.match, tr.match-row, article.game"):
            try:
                h_el = row.select_one(".local, .home, .equipo-a, .team-home")
                a_el = row.select_one(".visitante, .away, .equipo-b, .team-away")
                if not h_el or not a_el:
                    continue
                h, a = h_el.get_text(strip=True), a_el.get_text(strip=True)
                if not h or not a:
                    continue
                relevance, arg_team = detect_argentina_relevance(h, a, comp, "voley")
                if relevance == "none":
                    continue
                h_n = re.sub(r"\W+", "-", normalize_str(h))[:20]
                a_n = re.sub(r"\W+", "-", normalize_str(a))[:20]
                results.append(NormalizedMatch(
                    id=f"voley-ar-{h_n}-{a_n}",
                    sport="voley", source="voley.org.ar", competition=comp,
                    home_team=h, away_team=a, status="upcoming",
                    argentina_relevance=relevance, argentina_team=arg_team, raw={},
                ))
            except Exception:
                continue
        return results
