"""
Adapter de handball argentino.
Fuente primaria : IHF (ihf.info)
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

IHF_RESULTS_URL = "https://www.ihf.info/competitions/results"


class HandballAdapter(BaseScraper):
    EXTRA_HEADERS = {"Referer": "https://www.ihf.info/"}

    async def scrape(self) -> list[NormalizedMatch]:
        matches: list[NormalizedMatch] = []

        # Fuente 1: IHF
        try:
            html = await self.fetch_html(IHF_RESULTS_URL)
            local = self._parse_ihf(html)
            logger.info(f"[handball/ihf] {len(local)} con ARG")
            matches.extend(local)
        except Exception as e:
            logger.warning(f"[handball/ihf] falló: {e}")

        # Fallback: Sofascore
        try:
            data = await sofascore.get_events_by_date("handball")
            events = data.get("events", [])
            ss = sofascore_normalizer.normalize_events(events, "handball")
            existing = {m.id for m in matches}
            new = [m for m in ss if m.id not in existing]
            logger.info(f"[handball/sofascore-fallback] {len(new)} adicionales")
            matches.extend(new)
        except Exception as e:
            logger.warning(f"[handball/sofascore] falló: {e}")

        return matches

    def _parse_ihf(self, html: str) -> list[NormalizedMatch]:
        soup = BeautifulSoup(html, "lxml")
        results = []
        for row in soup.select("div.match, article.game, li.result-row, div.match-result"):
            try:
                team_tags = row.select(".team-name, .team, .club-name")
                if len(team_tags) < 2:
                    continue
                home = team_tags[0].get_text(strip=True)
                away = team_tags[1].get_text(strip=True)
                relevance, arg_team = detect_argentina_relevance(home, away, "", "handball")
                if relevance == "none":
                    continue
                score_tag = row.select_one(".score, .result")
                comp_tag  = row.find_previous(["div","h2","h3"], class_=["competition","event"])
                home_score = away_score = None
                if score_tag:
                    parts = re.findall(r"\d+", score_tag.get_text())
                    if len(parts) >= 2:
                        home_score, away_score = int(parts[0]), int(parts[1])
                status = "finished" if home_score is not None else "upcoming"
                competition = comp_tag.get_text(strip=True) if comp_tag else "IHF"
                home_slug = re.sub(r"\W+", "-", home.lower())[:20]
                away_slug = re.sub(r"\W+", "-", away.lower())[:20]
                results.append(NormalizedMatch(
                    id=f"handball-ihf-{home_slug}-{away_slug}",
                    sport="handball",
                    source="ihf",
                    competition=competition,
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
