"""
Adapter de hockey sobre césped argentino.

Fuentes:
1. Sofascore scheduled (field-hockey)
2. Sofascore live
3. FIH.ch HTML (fallback)

Cubre: Las Leonas, Los Leones, FIH Pro League, Liga Argentina.
"""
import logging
import re
from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch
from scraping.sources import sofascore
from scraping.normalizers import sofascore_normalizer
from scraping.argentina import detect_argentina_relevance, normalize_str

logger = logging.getLogger(__name__)

FIH_RESULTS  = "https://www.fih.ch/en/calendar-and-results/results/"
FIH_FIXTURES = "https://www.fih.ch/en/calendar-and-results/fixtures/"


class HockeyAdapter(BaseScraper):
    EXTRA_HEADERS = {"Referer": "https://www.fih.ch/"}

    async def scrape(self) -> list[NormalizedMatch]:
        matches: list[NormalizedMatch] = []

        # ── Fuente 1: Sofascore scheduled ─────────────────────────────────
        try:
            data = await sofascore.get_events_by_date("hockey")
            events = data.get("events", [])
            ss = sofascore_normalizer.normalize_events(events, "hockey")
            logger.info(f"[hockey/sofascore-scheduled] {len(ss)} con ARG (de {len(events)} total)")
            matches.extend(ss)
        except Exception as e:
            logger.warning(f"[hockey/sofascore-scheduled] falló: {e}")

        # ── Fuente 2: Sofascore live ───────────────────────────────────────
        try:
            data = await sofascore.get_live_events("hockey")
            events = data.get("events", [])
            live = sofascore_normalizer.normalize_events(events, "hockey")
            existing = {m.id for m in matches}
            new_live = [m for m in live if m.id not in existing]
            logger.info(f"[hockey/sofascore-live] {len(new_live)} en vivo")
            matches.extend(new_live)
        except Exception as e:
            logger.warning(f"[hockey/sofascore-live] falló: {e}")

        # ── Fuente 3: FIH HTML (solo si Sofascore falló) ──────────────────
        if not matches:
            for url, default_status in [(FIH_RESULTS, "finished"), (FIH_FIXTURES, "upcoming")]:
                try:
                    html = await self.fetch_html(url)
                    local = self._parse_fih(html, default_status)
                    existing = {m.id for m in matches}
                    new = [m for m in local if m.id not in existing]
                    logger.info(f"[hockey/fih-{default_status}] {len(new)} con ARG")
                    matches.extend(new)
                except Exception as e:
                    logger.warning(f"[hockey/fih-{default_status}] falló: {e}")

        logger.info(f"[hockey] TOTAL: {len(matches)}")
        return matches

    def _parse_fih(self, html: str, default_status: str) -> list[NormalizedMatch]:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        results = []

        for row in soup.select("div.match-result, article.match, div.fixture-row, li.result-item"):
            try:
                team_tags = row.select(".team-name, .team, span.name")
                if len(team_tags) < 2:
                    continue
                home = team_tags[0].get_text(strip=True)
                away = team_tags[1].get_text(strip=True)
                if not home or not away:
                    continue

                comp_tag = row.find_previous(
                    ["div", "h2", "h3", "span"],
                    class_=["competition-name", "event-name", "tournament"]
                )
                competition = comp_tag.get_text(strip=True) if comp_tag else "FIH Hockey"

                relevance, arg_team = detect_argentina_relevance(home, away, competition, "hockey")
                if relevance == "none":
                    continue

                score_tag = row.select_one(".score, .result-score, .goals")
                home_score = away_score = None
                if score_tag:
                    nums = re.findall(r"\d+", score_tag.get_text())
                    if len(nums) >= 2:
                        home_score, away_score = int(nums[0]), int(nums[1])
                status = "finished" if home_score is not None else default_status

                time_tag = row.select_one(".time, .match-time, .hour")
                home_n = re.sub(r"\W+", "-", normalize_str(home))[:20]
                away_n = re.sub(r"\W+", "-", normalize_str(away))[:20]
                results.append(NormalizedMatch(
                    id=f"hockey-fih-{home_n}-{away_n}",
                    sport="hockey", source="fih", competition=competition,
                    home_team=home, away_team=away,
                    home_score=home_score, away_score=away_score, status=status,
                    start_time_arg=time_tag.get_text(strip=True) if time_tag else None,
                    argentina_relevance=relevance, argentina_team=arg_team, raw={},
                ))
            except Exception:
                continue
        return results
