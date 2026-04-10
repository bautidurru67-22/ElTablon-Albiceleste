"""
Adapter de hockey sobre césped argentino.
Fuente primaria : FIH (fih.ch) — resultados y fixtures oficiales vía HTML
Fallback        : Sofascore field-hockey
Cubrir:
  - Las Leonas / Los Leones (selecciones)
  - Pro League (FIH Pro League)
  - Liga Argentina de Hockey
"""
import logging
import re
from datetime import date, datetime, timezone
from bs4 import BeautifulSoup

from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch
from scraping.sources import sofascore
from scraping.normalizers import sofascore_normalizer
from scraping.argentina import detect_argentina_relevance

logger = logging.getLogger(__name__)

FIH_RESULTS_URL = "https://www.fih.ch/en/calendar-and-results/results/"
FIH_FIXTURES_URL = "https://www.fih.ch/en/calendar-and-results/fixtures/"


class HockeyAdapter(BaseScraper):
    """
    Hockey sobre césped argentino.
    FIH primary → Sofascore fallback.
    """

    EXTRA_HEADERS = {"Referer": "https://www.fih.ch/"}

    async def scrape(self) -> list[NormalizedMatch]:
        matches: list[NormalizedMatch] = []

        # Fuente 1: FIH — resultados recientes
        try:
            html = await self.fetch_html(FIH_RESULTS_URL)
            finished = self._parse_fih(html, default_status="finished")
            arg = [m for m in finished if m.argentina_relevance != "none"]
            logger.info(f"[hockey/fih-results] {len(arg)} con ARG")
            matches.extend(arg)
        except Exception as e:
            logger.warning(f"[hockey/fih-results] falló: {e}")

        # Fuente 2: FIH — fixtures próximos
        try:
            html = await self.fetch_html(FIH_FIXTURES_URL)
            upcoming = self._parse_fih(html, default_status="upcoming")
            existing = {m.id for m in matches}
            arg = [m for m in upcoming if m.argentina_relevance != "none" and m.id not in existing]
            logger.info(f"[hockey/fih-fixtures] {len(arg)} con ARG")
            matches.extend(arg)
        except Exception as e:
            logger.warning(f"[hockey/fih-fixtures] falló: {e}")

        # Fuente 3: Sofascore fallback (cubre partidos no listados en FIH)
        try:
            data = await sofascore.get_events_by_date("hockey")
            events = data.get("events", [])
            ss = sofascore_normalizer.normalize_events(events, "hockey")
            existing = {m.id for m in matches}
            new = [m for m in ss if m.id not in existing]
            logger.info(f"[hockey/sofascore] {len(new)} adicionales")
            matches.extend(new)
        except Exception as e:
            logger.warning(f"[hockey/sofascore] falló: {e}")

        # En vivo vía Sofascore
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

        return matches

    def _parse_fih(self, html: str, default_status: str) -> list[NormalizedMatch]:
        """
        Parsea resultados/fixtures del sitio fih.ch.
        Estructura HTML a confirmar en producción (selectores probables).
        """
        soup = BeautifulSoup(html, "lxml")
        results: list[NormalizedMatch] = []

        # FIH estructura típica: article.match-result o div.result-row
        for row in soup.select(
            "div.match-result, article.match, div.fixture-row, li.result-item"
        ):
            try:
                # Equipos
                team_tags = row.select(".team-name, .team, span.name")
                if len(team_tags) < 2:
                    continue
                home = team_tags[0].get_text(strip=True)
                away = team_tags[1].get_text(strip=True)
                if not home or not away:
                    continue

                # Competencia
                comp_tag = row.find_previous(
                    ["div", "h2", "h3", "span"],
                    class_=["competition-name", "event-name", "tournament"]
                )
                competition = comp_tag.get_text(strip=True) if comp_tag else "FIH Hockey"

                # Score
                home_score = away_score = None
                score_tag = row.select_one(".score, .result-score, .goals")
                if score_tag:
                    score_text = score_tag.get_text(strip=True)
                    parts = re.findall(r"\d+", score_text)
                    if len(parts) >= 2:
                        home_score, away_score = int(parts[0]), int(parts[1])

                # Status
                status_tag = row.select_one(".status, .match-status, .state")
                status_text = status_tag.get_text(strip=True).lower() if status_tag else ""
                if "live" in status_text or "en juego" in status_text:
                    status = "live"
                elif home_score is not None:
                    status = "finished"
                else:
                    status = default_status

                # Hora
                time_tag = row.select_one(".time, .match-time, .hour")
                start_time = time_tag.get_text(strip=True) if time_tag else None

                relevance, arg_team = detect_argentina_relevance(
                    home, away, competition, "hockey"
                )

                home_slug = re.sub(r"\W+", "-", home.lower())[:20]
                away_slug = re.sub(r"\W+", "-", away.lower())[:20]

                results.append(NormalizedMatch(
                    id=f"hockey-fih-{home_slug}-{away_slug}",
                    sport="hockey",
                    source="fih",
                    competition=competition,
                    home_team=home,
                    away_team=away,
                    home_score=home_score,
                    away_score=away_score,
                    status=status,
                    start_time_arg=start_time,
                    argentina_relevance=relevance,
                    argentina_team=arg_team,
                    raw={},
                ))
            except Exception:
                continue

        return results
