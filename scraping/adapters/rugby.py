"""
Adapter de rugby argentino.

Fuentes:
1. Sofascore scheduled (rugby-union) — principal
2. Sofascore live                    — en vivo
3. UAR.com.ar HTML                   — fallback local

Cubre: Los Pumas, Pumitas, Argentina 7s, SuperRugby Américas, URBA.
"""
import logging
import re
from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch
from scraping.sources import sofascore
from scraping.normalizers import sofascore_normalizer
from scraping.argentina import detect_argentina_relevance, normalize_str

logger = logging.getLogger(__name__)

UAR_FIXTURE_URL = "https://www.uar.com.ar/fixture-y-resultados"


class RugbyAdapter(BaseScraper):
    EXTRA_HEADERS = {"Referer": "https://www.uar.com.ar/"}

    async def scrape(self) -> list[NormalizedMatch]:
        matches: list[NormalizedMatch] = []

        # ── Fuente 1: Sofascore scheduled ─────────────────────────────────
        try:
            data = await sofascore.get_events_by_date("rugby")
            events = data.get("events", [])
            ss = sofascore_normalizer.normalize_events(events, "rugby")
            logger.info(f"[rugby/sofascore-scheduled] {len(ss)} con ARG (de {len(events)} total)")
            matches.extend(ss)
        except Exception as e:
            logger.warning(f"[rugby/sofascore-scheduled] falló: {e}")

        # ── Fuente 2: Sofascore live ───────────────────────────────────────
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

        # ── Fuente 3: UAR HTML (solo si Sofascore no devolvió nada) ───────
        if not matches:
            try:
                html = await self.fetch_html(UAR_FIXTURE_URL)
                local = self._parse_uar(html)
                logger.info(f"[rugby/uar-fallback] {len(local)} partidos")
                matches.extend(local)
            except Exception as e:
                logger.warning(f"[rugby/uar-fallback] falló: {e}")

        logger.info(f"[rugby] TOTAL: {len(matches)}")
        return matches

    def _parse_uar(self, html: str) -> list[NormalizedMatch]:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        results = []
        comp = "Rugby Argentina"

        for row in soup.select("div.partido, article.match, div.fixture-item, li.match-item"):
            try:
                home_tag = row.select_one(".local, .home, .team-home, .equipo1")
                away_tag = row.select_one(".visitante, .away, .team-away, .equipo2")
                if not home_tag or not away_tag:
                    continue
                home = home_tag.get_text(strip=True)
                away = away_tag.get_text(strip=True)
                if not home or not away:
                    continue

                relevance, arg_team = detect_argentina_relevance(home, away, comp, "rugby")
                if relevance == "none":
                    continue

                score_tag = row.select_one(".resultado, .score, .puntos")
                time_tag  = row.select_one(".hora, .time, .horario")
                home_score = away_score = None
                score_text = score_tag.get_text(strip=True) if score_tag else ""
                if "-" in score_text:
                    parts = score_text.split("-")
                    if len(parts) == 2:
                        try:
                            home_score, away_score = int(parts[0].strip()), int(parts[1].strip())
                        except ValueError:
                            pass
                status = "finished" if home_score is not None else "upcoming"

                home_n = re.sub(r"\W+", "-", normalize_str(home))[:20]
                away_n = re.sub(r"\W+", "-", normalize_str(away))[:20]
                results.append(NormalizedMatch(
                    id=f"rugby-uar-{home_n}-{away_n}",
                    sport="rugby", source="uar", competition=comp,
                    home_team=home, away_team=away,
                    home_score=home_score, away_score=away_score, status=status,
                    start_time_arg=time_tag.get_text(strip=True) if time_tag else None,
                    argentina_relevance=relevance, argentina_team=arg_team, raw={},
                ))
            except Exception:
                continue
        return results
