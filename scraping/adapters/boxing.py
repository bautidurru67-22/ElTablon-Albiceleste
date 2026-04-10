"""
Adapter de boxeo argentino.
Fuente primaria : BoxRec (boxrec.com/schedule)
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

BOXREC_SCHEDULE = "https://boxrec.com/en/schedule"


class BoxingAdapter(BaseScraper):
    EXTRA_HEADERS = {"Referer": "https://boxrec.com/"}

    async def scrape(self) -> list[NormalizedMatch]:
        matches: list[NormalizedMatch] = []

        # Fuente 1: BoxRec schedule
        try:
            html = await self.fetch_html(BOXREC_SCHEDULE)
            local = self._parse_boxrec(html)
            logger.info(f"[boxing/boxrec] {len(local)} con ARG")
            matches.extend(local)
        except Exception as e:
            logger.warning(f"[boxing/boxrec] falló (BoxRec requiere login para algunas páginas): {e}")

        # Fallback: Sofascore
        try:
            data = await sofascore.get_events_by_date("boxeo")
            events = data.get("events", [])
            ss = sofascore_normalizer.normalize_events(events, "boxeo")
            existing = {m.id for m in matches}
            new = [m for m in ss if m.id not in existing]
            logger.info(f"[boxing/sofascore-fallback] {len(new)} adicionales")
            matches.extend(new)
        except Exception as e:
            logger.warning(f"[boxing/sofascore] falló: {e}")

        return matches

    def _parse_boxrec(self, html: str) -> list[NormalizedMatch]:
        soup = BeautifulSoup(html, "lxml")
        results = []
        for row in soup.select("tr.scheduleRow, div.bout-row, li.fight"):
            try:
                fighter_tags = row.select(".fighter, .boxer, td.fighter-name, a.fighter")
                if len(fighter_tags) < 2:
                    continue
                home = fighter_tags[0].get_text(strip=True)
                away = fighter_tags[1].get_text(strip=True)
                relevance, arg_team = detect_argentina_relevance(home, away, "", "boxeo")
                if relevance == "none":
                    continue
                date_tag  = row.select_one(".date, td.date, .fight-date")
                venue_tag = row.select_one(".venue, .location, td.venue")
                title_tag = row.select_one(".title, .belt, .championship")
                competition = title_tag.get_text(strip=True) if title_tag else "Boxeo"
                start_time = date_tag.get_text(strip=True) if date_tag else None
                home_slug = re.sub(r"\W+", "-", home.lower())[:20]
                away_slug = re.sub(r"\W+", "-", away.lower())[:20]
                results.append(NormalizedMatch(
                    id=f"boxeo-boxrec-{home_slug}-{away_slug}",
                    sport="boxeo",
                    source="boxrec",
                    competition=competition,
                    home_team=home,
                    away_team=away,
                    status="upcoming",
                    start_time_arg=start_time,
                    argentina_relevance=relevance,
                    argentina_team=arg_team,
                    raw={},
                ))
            except Exception:
                continue
        return results
