"""
MotoGP — API oficial api.motogp.com + Sofascore fallback.
"""
import logging
import re
from datetime import date
from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch
from scraping.sources.motogp_api import get_calendar, is_active_event, parse_event_to_match

logger = logging.getLogger(__name__)


class MotoGPAdapter(BaseScraper):

    async def scrape(self) -> list[NormalizedMatch]:
        matches: list[NormalizedMatch] = []
        today = date.today()

        try:
            events = await get_calendar()
            if not isinstance(events, list):
                events = []
            for ev in events:
                start = ev.get("date_start", "")
                end   = ev.get("date_end", "")
                try:
                    from datetime import date as d_
                    s = d_.fromisoformat(start[:10])
                    e = d_.fromisoformat(end[:10]) if end else s
                except Exception:
                    continue
                # Incluir eventos en un rango de ±3 días
                if not (abs((s - today).days) <= 3 or s <= today <= e):
                    continue

                raw = parse_event_to_match(ev)
                status = "upcoming"
                if s <= today <= e:
                    status = "live"
                elif today > e:
                    status = "finished"

                gp = ev.get("name", "Grand Prix")
                country_d = ev.get("country") or {}
                country = country_d.get("name", "") if isinstance(country_d, dict) else ""
                circuit_d = ev.get("circuit") or {}
                circuit = circuit_d.get("name", "") if isinstance(circuit_d, dict) else ""
                mid = re.sub(r"\W+", "-", f"{gp}-{start[:10]}")[:40].lower()

                matches.append(NormalizedMatch(
                    id=f"motogp-{mid}",
                    sport="motogp", source="motogp",
                    competition=f"MotoGP — {country}".strip(" —"),
                    home_team=gp,
                    away_team=circuit or country,
                    status=status,
                    start_time_arg=start[:10],
                    argentina_relevance="jugador_arg",
                    argentina_team="Augusto Fernández",
                    broadcast="ESPN",
                    raw=ev,
                ))
            logger.info(f"[motogp/api] {len(matches)} eventos")
        except Exception as e:
            logger.warning(f"[motogp/api] {e}")

        logger.info(f"[motogp] TOTAL {len(matches)}")
        return matches
