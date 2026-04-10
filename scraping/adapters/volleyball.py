"""
Adapter de vóley argentino.
Fuente primaria : FIVB / Volleyball World (volleyballworld.com)
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

FIVB_SCORES_URL = "https://en.volleyballworld.com/volleyball/competitions/results/"


class VolleyballAdapter(BaseScraper):
    """
    Vóley argentino:
      - Las Panteras / Selección masculina
      - VNL (Volleyball Nations League)
      - Campeonato Mundial / FIVB eventos
      - Liga de Voleibol Argentina
    """
    EXTRA_HEADERS = {"Referer": "https://en.volleyballworld.com/"}

    async def scrape(self) -> list[NormalizedMatch]:
        matches: list[NormalizedMatch] = []

        # Fuente 1: FIVB Volleyball World
        try:
            html = await self.fetch_html(FIVB_SCORES_URL)
            local = self._parse_fivb(html)
            logger.info(f"[volleyball/fivb] {len(local)} con ARG")
            matches.extend(local)
        except Exception as e:
            logger.warning(f"[volleyball/fivb] falló: {e}")

        # Fallback: Sofascore
        try:
            data = await sofascore.get_events_by_date("voley")
            events = data.get("events", [])
            ss = sofascore_normalizer.normalize_events(events, "voley")
            existing = {m.id for m in matches}
            new = [m for m in ss if m.id not in existing]
            logger.info(f"[volleyball/sofascore-fallback] {len(new)} adicionales")
            matches.extend(new)
        except Exception as e:
            logger.warning(f"[volleyball/sofascore] falló: {e}")

        return matches

    def _parse_fivb(self, html: str) -> list[NormalizedMatch]:
        soup = BeautifulSoup(html, "lxml")
        results = []
        for row in soup.select("div.match-card, article.result, li.match-result, div.game-row"):
            try:
                team_tags = row.select(".team-name, .team, span.name")
                if len(team_tags) < 2:
                    continue
                home = team_tags[0].get_text(strip=True)
                away = team_tags[1].get_text(strip=True)
                relevance, arg_team = detect_argentina_relevance(home, away, "", "voley")
                if relevance == "none":
                    continue

                score_tag = row.select_one(".score, .result, .sets")
                comp_tag  = row.find_previous(["div","h2","h3"], class_=["competition","event","league"])
                time_tag  = row.select_one(".time, .hour, .match-time")

                home_score = away_score = None
                score_text = score_tag.get_text(strip=True) if score_tag else ""
                if "-" in score_text:
                    parts = score_text.split("-")
                    if len(parts) == 2:
                        try:
                            home_score = int(parts[0].strip())
                            away_score = int(parts[1].strip())
                        except ValueError:
                            pass

                status = "finished" if home_score is not None else "upcoming"
                competition = comp_tag.get_text(strip=True) if comp_tag else "FIVB"
                home_slug = re.sub(r"\W+", "-", home.lower())[:20]
                away_slug = re.sub(r"\W+", "-", away.lower())[:20]

                results.append(NormalizedMatch(
                    id=f"voley-fivb-{home_slug}-{away_slug}",
                    sport="voley",
                    source="fivb",
                    competition=competition,
                    home_team=home,
                    away_team=away,
                    home_score=home_score,
                    away_score=away_score,
                    status=status,
                    start_time_arg=time_tag.get_text(strip=True) if time_tag else None,
                    argentina_relevance=relevance,
                    argentina_team=arg_team,
                    raw={},
                ))
            except Exception:
                continue
        return results
