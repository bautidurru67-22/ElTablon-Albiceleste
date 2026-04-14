"""
Adapter de tenis argentino.

Fuentes:
1. Sofascore scheduled (tenis)  — fixture del día
2. Sofascore live               — partidos en vivo
3. ATP Tour HTML                — fallback si Sofascore falla

Filtra solo partidos con jugadores argentinos (ARG_PLAYERS).
"""
import logging
import re
from bs4 import BeautifulSoup
from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch
from scraping.sources import sofascore
from scraping.normalizers import sofascore_normalizer, tennis_normalizer
from scraping.argentina import ARG_PLAYERS

logger = logging.getLogger(__name__)

ATP_SCORES_URL = "https://www.atptour.com/en/scores/current"


class TennisAdapter(BaseScraper):
    SOURCE_ORDER = ["sofascore_scheduled", "sofascore_live", "atptour"]
    DIAG_VERSION = "tennis-diag-v1-2026-04-14"
    LAST_RUN: dict = {}
    EXTRA_HEADERS = {"Referer": "https://www.sofascore.com/"}

    async def scrape(self) -> list[NormalizedMatch]:
        matches: list[NormalizedMatch] = []

        # ── Fuente 1: Sofascore scheduled ─────────────────────────────────
        try:
            data = await sofascore.get_events_by_date("tenis")
            events = data.get("events", [])
            ss = sofascore_normalizer.normalize_events(events, "tenis")
            if not ss:
                ss = sofascore_normalizer.normalize_events_all(events, "tenis")
            logger.info(f"[tennis/sofascore-scheduled] {len(ss)}")
            matches.extend(ss)
        except Exception as e:
            logger.warning(f"[tennis/sofascore-scheduled] falló: {e}")

        # ── Fuente 2: Sofascore live ───────────────────────────────────────
        try:
            data = await sofascore.get_live_events("tenis")
            events = data.get("events", [])
            live = sofascore_normalizer.normalize_events(events, "tenis")
            if not live:
                live = sofascore_normalizer.normalize_events_all(events, "tenis")
            existing = {m.id for m in matches}
            new_live = [m for m in live if m.id not in existing]
            logger.info(f"[tennis/sofascore-live] {len(new_live)} en vivo")
            matches.extend(new_live)
        except Exception as e:
            logger.warning(f"[tennis/sofascore-live] falló: {e}")

        # ── Fuente 3: ATP HTML (solo si Sofascore falló completamente) ─────
        if not matches:
            try:
                html = await self.fetch_html(ATP_SCORES_URL)
                raws = self._parse_atp(html)
                atp = tennis_normalizer.normalize_matches(raws)
                arg = [m for m in atp if m.argentina_relevance != "none"]
                logger.info(f"[tennis/atp-fallback] {len(arg)} con ARG")
                matches.extend(arg)
            except Exception as e:
                logger.warning(f"[tennis/atp-fallback] falló: {e}")

        logger.info(f"[tennis] TOTAL: {len(matches)} partidos")
        return matches

    def _parse_atp(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        raws = []
        arg_lower = set(ARG_PLAYERS.keys())

        for match_div in soup.select(
            "div.match-ctr, div.scores-day-match, li.match, div[class*='match']"
        ):
            try:
                player_tags = match_div.select(".player-name, .name, .player, [class*='player']")
                if len(player_tags) < 2:
                    continue
                p1 = player_tags[0].get_text(strip=True)
                p2 = player_tags[1].get_text(strip=True)
                p1l, p2l = p1.lower(), p2.lower()
                if not any(a in p1l or a in p2l for a in arg_lower):
                    continue

                score_tag = match_div.select_one(".score, .sets, .match-score")
                status_tag = match_div.select_one(".status, .match-status")
                comp_tag = match_div.find_previous(
                    ["div", "h2", "h3"],
                    class_=["tournament-name", "event-header", "tourn-name"]
                )

                score_raw = score_tag.get_text(strip=True) if score_tag else ""
                status_text = status_tag.get_text(strip=True).lower() if status_tag else ""
                competition = comp_tag.get_text(strip=True) if comp_tag else "ATP Tour"

                if "live" in status_text or "in progress" in status_text:
                    status = "live"
                elif score_raw:
                    status = "finished"
                else:
                    status = "upcoming"

                raws.append({
                    "player1": p1,
                    "player2": p2,
                    "score_raw": score_raw,
                    "status": status,
                    "competition": competition,
                    "source": "atptour",
                })
            except Exception:
                continue
        return raws
