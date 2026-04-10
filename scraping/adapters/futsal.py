"""
Adapter de futsal argentino.
Fuente primaria : AFA Futsal (afa.com.ar/futsal) + AMF
Fallback        : Sofascore
"""
import logging
import re
from bs4 import BeautifulSoup
from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch
from scraping.sources import sofascore
from scraping.normalizers import sofascore_normalizer
from scraping.argentina import detect_argentina_relevance

logger = logging.getLogger(__name__)

AFA_FUTSAL_URL = "https://www.afa.com.ar/es/competencia/futsal"
AMF_URL        = "https://www.amffutsal.com/competitions"


class FutsalAdapter(BaseScraper):
    EXTRA_HEADERS = {"Referer": "https://www.afa.com.ar/"}

    async def scrape(self) -> list[NormalizedMatch]:
        matches: list[NormalizedMatch] = []

        # Fuente 1: AFA Futsal
        try:
            html = await self.fetch_html(AFA_FUTSAL_URL)
            local = self._parse_generic(html, "afa-futsal", "Liga Nacional de Futsal")
            logger.info(f"[futsal/afa] {len(local)} con ARG")
            matches.extend(local)
        except Exception as e:
            logger.warning(f"[futsal/afa] falló: {e}")

        # Fallback: Sofascore
        try:
            data = await sofascore.get_events_by_date("futsal")
            events = data.get("events", [])
            ss = sofascore_normalizer.normalize_events(events, "futsal")
            existing = {m.id for m in matches}
            new = [m for m in ss if m.id not in existing]
            logger.info(f"[futsal/sofascore-fallback] {len(new)} adicionales")
            matches.extend(new)
        except Exception as e:
            logger.warning(f"[futsal/sofascore] falló: {e}")

        return matches

    def _parse_generic(self, html: str, source: str, default_comp: str) -> list[NormalizedMatch]:
        soup = BeautifulSoup(html, "lxml")
        results = []
        for row in soup.select("div.partido, article.match, li.fixture, div.game"):
            try:
                team_tags = row.select(".equipo, .team, .club")
                if len(team_tags) < 2:
                    continue
                home = team_tags[0].get_text(strip=True)
                away = team_tags[1].get_text(strip=True)
                relevance, arg_team = detect_argentina_relevance(home, away, default_comp, "futsal")
                if relevance == "none":
                    continue
                score_tag = row.select_one(".resultado, .score")
                home_score = away_score = None
                if score_tag:
                    parts = re.findall(r"\d+", score_tag.get_text())
                    if len(parts) >= 2:
                        home_score, away_score = int(parts[0]), int(parts[1])
                status = "finished" if home_score is not None else "upcoming"
                home_slug = re.sub(r"\W+", "-", home.lower())[:20]
                away_slug = re.sub(r"\W+", "-", away.lower())[:20]
                results.append(NormalizedMatch(
                    id=f"futsal-{source}-{home_slug}-{away_slug}",
                    sport="futsal",
                    source=source,
                    competition=default_comp,
                    home_team=home,
                    away_team=away,
                    home_score=home_score,
                    away_score=away_score,
                    status=status,
                    argentina_relevance=relevance,
                    argentina_team=arg_team,
                    raw={},
                ))
            except Exception:
                continue
        return results
