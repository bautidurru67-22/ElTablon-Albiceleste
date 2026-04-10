"""
Adapter de MotoGP argentino.
Fuente primaria : MotoGP API oficial (api.motogp.com)
Fallback        : Sofascore
"""
import logging
from datetime import date
from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch
from scraping.sources import sofascore, motogp_api
from scraping.normalizers import sofascore_normalizer

logger = logging.getLogger(__name__)


class MotoGPAdapter(BaseScraper):
    async def scrape(self) -> list[NormalizedMatch]:
        matches: list[NormalizedMatch] = []

        # Fuente 1: MotoGP API oficial
        try:
            calendar = await motogp_api.get_calendar()
            if isinstance(calendar, list):
                for event in calendar:
                    if not motogp_api.is_active_event(event):
                        continue
                    raw = motogp_api.parse_event_to_match(event)
                    m = NormalizedMatch(
                        id=f"motogp-{event.get('id', 'evt')}",
                        sport="motogp",
                        source="motogp",
                        competition=f"MotoGP — {event.get('name', 'Grand Prix')}",
                        home_team="Carrera",
                        away_team=event.get("circuit", {}).get("name", ""),
                        status="upcoming",
                        start_time_arg=event.get("date_start", "")[:10],
                        argentina_relevance="jugador_arg",
                        argentina_team="Augusto Fernández",
                        raw=event,
                    )
                    matches.append(m)
            logger.info(f"[motogp/api] {len(matches)} eventos activos")
        except Exception as e:
            logger.warning(f"[motogp/api] falló: {e}")

        # Fallback: Sofascore
        try:
            data = await sofascore.get_events_by_date("motogp")
            events = data.get("events", [])
            ss = sofascore_normalizer.normalize_events(events, "motogp")
            existing = {m.id for m in matches}
            new = [m for m in ss if m.id not in existing]
            logger.info(f"[motogp/sofascore-fallback] {len(new)} adicionales")
            matches.extend(new)
        except Exception as e:
            logger.warning(f"[motogp/sofascore] falló: {e}")

        return matches
