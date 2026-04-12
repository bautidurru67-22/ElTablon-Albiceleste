"""
Adapter MotoGP — API oficial motogp.com + Sofascore fallback.

La API oficial retorna el calendario con fechas de inicio/fin de cada evento.
Filtra eventos activos hoy ±2 días.
"""
import logging
from datetime import date, datetime, timezone
from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch
from scraping.sources import sofascore
from scraping.normalizers import sofascore_normalizer

logger = logging.getLogger(__name__)


class MotoGPAdapter(BaseScraper):

    async def scrape(self) -> list[NormalizedMatch]:
        matches = []
        today = date.today()

        # ── 1. MotoGP API oficial ──────────────────────────────────────────
        try:
            url = f"https://api.motogp.com/riders-api/season/{today.year}/events?test=false"
            events = await self.fetch_json(url)
            if isinstance(events, list):
                for ev in events:
                    start_str = ev.get("date_start", "")
                    end_str   = ev.get("date_end", "")
                    if not start_str:
                        continue
                    try:
                        start_d = date.fromisoformat(start_str[:10])
                        end_d   = date.fromisoformat(end_str[:10]) if end_str else start_d
                    except Exception:
                        continue
                    # Incluir eventos de esta semana (±3 días)
                    if not (abs((start_d - today).days) <= 3 or start_d <= today <= end_d):
                        continue

                    circuit = ev.get("circuit", {})
                    circuit_name = circuit.get("name", "") if isinstance(circuit, dict) else ""
                    country = ev.get("country", {})
                    country_name = country.get("name", "") if isinstance(country, dict) else ""
                    event_name = ev.get("name", "Grand Prix")

                    status = "upcoming"
                    if start_d <= today <= end_d:
                        status = "live"
                    elif today > end_d:
                        status = "finished"

                    matches.append(NormalizedMatch(
                        id=f"motogp-{ev.get('id', start_str)}",
                        sport="motogp", source="motogp",
                        competition=f"MotoGP — {country_name}".strip(" —"),
                        home_team=event_name,
                        away_team=f"{circuit_name}".strip(),
                        status=status,
                        start_time_arg=start_str[:10],
                        argentina_relevance="jugador_arg",
                        argentina_team="Augusto Fernández",
                        broadcast="ESPN",
                        raw=ev,
                    ))
            logger.info(f"[motogp/api] {len(matches)} eventos")
        except Exception as e:
            logger.warning(f"[motogp/api] {e}")

        # ── 2. Sofascore fallback ──────────────────────────────────────────
        if not matches:
            try:
                data = await sofascore.get_events_by_date("motogp")
                events_ss = data.get("events", [])
                ss = sofascore_normalizer.normalize_events(events_ss, "motogp")
                logger.info(f"[motogp/sofascore] {len(ss)} con ARG")
                matches.extend(ss)
            except Exception as e:
                logger.warning(f"[motogp/sofascore] {e}")

        logger.info(f"[motogp] TOTAL {len(matches)}")
        return matches
