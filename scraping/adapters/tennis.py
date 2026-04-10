"""
Adapter de tenis argentino.
Fuente primaria: ATP Tour (HTML scraping, filtrando ARG)
Fallback: Sofascore API
"""
import logging
from bs4 import BeautifulSoup
from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch
from scraping.sources import atptour, sofascore
from scraping.normalizers import tennis_normalizer, sofascore_normalizer
from scraping.argentina import ARG_PLAYERS

logger = logging.getLogger(__name__)

# Torneos ATP actualmente activos (se puede ampliar)
CURRENT_TOURNAMENTS: list[dict] = [
    {"name": "ATP Madrid · Masters 1000", "url": None},   # usa página principal ATP
]


class TennisAdapter(BaseScraper):
    """
    Tenis argentino: ATP, WTA, Challenger, Copa Davis.
    Filtra solo partidos donde juegue un argentino.
    """
    EXTRA_HEADERS = {"Referer": "https://www.atptour.com/"}

    async def scrape(self) -> list[NormalizedMatch]:
        matches: list[NormalizedMatch] = []

        # --- Fuente 1: ATP Tour HTML ---
        try:
            html = await atptour.get_today_scores()
            raws = self._parse_atp_html(html)
            atp = tennis_normalizer.normalize_matches(raws)
            arg_only = [m for m in atp if m.argentina_relevance != "none"]
            logger.info(f"[tennis/atptour] {len(arg_only)} partidos con ARG")
            matches.extend(arg_only)
        except Exception as e:
            logger.warning(f"[tennis/atptour] falló: {e}")

        # --- Fuente 2: Sofascore (fallback + Challenger + Copa Davis) ---
        try:
            data = await sofascore.get_events_by_date("tenis")
            events = data.get("events", [])
            ss = sofascore_normalizer.normalize_events(events, "tenis")
            existing_ids = {m.id for m in matches}
            new = [m for m in ss if m.id not in existing_ids]
            logger.info(f"[tennis/sofascore] {len(new)} partidos adicionales")
            matches.extend(new)
        except Exception as e:
            logger.warning(f"[tennis/sofascore] falló: {e}")

        # --- En vivo ---
        try:
            data = await sofascore.get_live_events("tenis")
            events = data.get("events", [])
            live = sofascore_normalizer.normalize_events(events, "tenis")
            existing_ids = {m.id for m in matches}
            new_live = [m for m in live if m.id not in existing_ids]
            logger.info(f"[tennis/sofascore-live] {len(new_live)} en vivo")
            matches.extend(new_live)
        except Exception as e:
            logger.warning(f"[tennis/sofascore-live] falló: {e}")

        return matches

    def _parse_atp_html(self, html: str) -> list[dict]:
        """
        Parsea el HTML de atptour.com/en/scores/current.
        Extrae partidos donde algún jugador sea argentino.
        """
        soup = BeautifulSoup(html, "lxml")
        raws = []
        arg_lower = set(ARG_PLAYERS.keys())

        # ATP usa una estructura de tipo tabla con divs por match
        # Selector real: revisar DOM en producción
        # Estructura típica: div.match-ctr > div.player-name + div.set-scores
        for match_div in soup.select("div.match-ctr, div.scores-day-match, li.match"):
            try:
                player_tags = match_div.select(".player-name, .name, .player")
                if len(player_tags) < 2:
                    continue

                p1 = player_tags[0].get_text(strip=True)
                p2 = player_tags[1].get_text(strip=True)

                # Solo procesar si hay un argentino
                p1_lower = p1.lower()
                p2_lower = p2.lower()
                is_arg = any(a in p1_lower or a in p2_lower for a in arg_lower)
                if not is_arg:
                    continue

                score_tag = match_div.select_one(".score, .sets, .match-score")
                score_raw = score_tag.get_text(strip=True) if score_tag else ""

                status_tag = match_div.select_one(".status, .match-status")
                status_text = status_tag.get_text(strip=True).lower() if status_tag else ""
                if "live" in status_text or "in progress" in status_text:
                    status = "live"
                elif score_raw and "vs" not in score_raw.lower():
                    status = "finished"
                else:
                    status = "upcoming"

                # Competition: buscar en header anterior
                comp_tag = match_div.find_previous(
                    ["div", "h2", "h3"],
                    class_=["tournament-name", "event-header", "tourn-name"]
                )
                competition = comp_tag.get_text(strip=True) if comp_tag else "ATP Tour"

                time_tag = match_div.select_one(".time, .match-time")
                start_time = time_tag.get_text(strip=True) if time_tag else None

                raws.append({
                    "player1": p1,
                    "player2": p2,
                    "score_raw": score_raw,
                    "status": status,
                    "competition": competition,
                    "start_time": start_time,
                    "source": "atptour",
                })
            except Exception:
                continue

        return raws
