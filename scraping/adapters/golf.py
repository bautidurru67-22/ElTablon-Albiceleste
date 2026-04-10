"""
Adapter de golf argentino.
Fuente primaria : DP World Tour + PGA Tour (HTML leaderboard)
Fallback        : Sofascore
"""
import logging
import re
from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch
from scraping.sources import sofascore, golf_tours
from scraping.normalizers import sofascore_normalizer

logger = logging.getLogger(__name__)


class GolfAdapter(BaseScraper):
    EXTRA_HEADERS = {"Referer": "https://www.dpwtour.com/"}

    async def scrape(self) -> list[NormalizedMatch]:
        matches: list[NormalizedMatch] = []

        # Fuente 1: DP World Tour leaderboard
        try:
            html = await self.fetch_html(golf_tours.DPWT_SCORES)
            players = golf_tours.parse_leaderboard(html, "dpwt")
            for p in players:
                matches.append(self._player_to_match(p))
            logger.info(f"[golf/dpwt] {len(players)} jugadores ARG encontrados")
        except Exception as e:
            logger.warning(f"[golf/dpwt] falló: {e}")

        # Fuente 2: PGA Tour
        try:
            html = await self.fetch_html(golf_tours.PGA_SCORES)
            players = golf_tours.parse_leaderboard(html, "pga")
            existing = {m.id for m in matches}
            for p in players:
                m = self._player_to_match(p)
                if m.id not in existing:
                    matches.append(m)
            logger.info(f"[golf/pga] {len(players)} jugadores ARG encontrados")
        except Exception as e:
            logger.warning(f"[golf/pga] falló: {e}")

        # Fallback: Sofascore
        try:
            data = await sofascore.get_events_by_date("golf")
            events = data.get("events", [])
            ss = sofascore_normalizer.normalize_events(events, "golf")
            existing = {m.id for m in matches}
            new = [m for m in ss if m.id not in existing]
            logger.info(f"[golf/sofascore-fallback] {len(new)} adicionales")
            matches.extend(new)
        except Exception as e:
            logger.warning(f"[golf/sofascore] falló: {e}")

        return matches

    def _player_to_match(self, p: dict) -> NormalizedMatch:
        player = p.get("player", "")
        tournament = p.get("tournament", "Golf Tournament")
        source = p.get("source", "golf")
        slug = re.sub(r"\W+", "-", player.lower())[:25]
        return NormalizedMatch(
            id=f"golf-{source}-{slug}",
            sport="golf",
            source=source,
            competition=tournament,
            home_team=player,
            away_team=f"Pos {p.get('position','?')}",
            score_detail=p.get("score", ""),
            status="live",
            argentina_relevance="jugador_arg",
            argentina_team=player,
            raw=p,
        )
