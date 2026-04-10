"""
Adapter de automovilismo argentino.
Fuente primaria : OpenF1 API + Ergast API (F1) — ambas gratuitas
Fallback        : Sofascore
"""
import logging
import re
from datetime import date
from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch
from scraping.sources import sofascore, openf1
from scraping.normalizers import sofascore_normalizer
from scraping.argentina import ARG_PLAYERS

logger = logging.getLogger(__name__)

ARG_F1_DRIVERS = {"colapinto", "franco colapinto"}


class MotorsportAdapter(BaseScraper):
    """
    Automovilismo argentino:
      - F1: Franco Colapinto (OpenF1 + Ergast)
      - Turismo Carretera / TC2000 (ACTC) — stub dentro del adapter
    """
    async def scrape(self) -> list[NormalizedMatch]:
        matches: list[NormalizedMatch] = []

        # Fuente 1: Ergast — próxima/última carrera F1
        try:
            data = await openf1.get_current_race_weekend()
            races = (
                data.get("MRData", {})
                    .get("RaceTable", {})
                    .get("Races", [])
            )
            today = date.today().isoformat()
            for race in races:
                race_date = race.get("date", "")
                if not race_date:
                    continue
                # Solo publicar si es hoy, mañana o ayer (ventana de 3 días)
                from datetime import timedelta
                race_d = date.fromisoformat(race_date)
                delta = abs((race_d - date.today()).days)
                if delta > 1:
                    continue
                m = self._race_to_match(race)
                if m:
                    matches.append(m)
            logger.info(f"[motorsport/ergast] {len(matches)} eventos F1")
        except Exception as e:
            logger.warning(f"[motorsport/ergast] falló: {e}")

        # Fuente 2: OpenF1 — sesión activa hoy
        try:
            sessions = await openf1.get_current_session()
            if isinstance(sessions, list) and sessions:
                for session in sessions[:2]:
                    m = self._session_to_match(session)
                    if m and m.id not in {x.id for x in matches}:
                        matches.append(m)
        except Exception as e:
            logger.warning(f"[motorsport/openf1] falló: {e}")

        # Fallback: Sofascore
        try:
            data = await sofascore.get_events_by_date("motorsport")
            events = data.get("events", [])
            ss = sofascore_normalizer.normalize_events(events, "motorsport")
            existing = {m.id for m in matches}
            new = [m for m in ss if m.id not in existing]
            logger.info(f"[motorsport/sofascore-fallback] {len(new)} adicionales")
            matches.extend(new)
        except Exception as e:
            logger.warning(f"[motorsport/sofascore] falló: {e}")

        return matches

    def _race_to_match(self, race: dict) -> NormalizedMatch | None:
        try:
            name = race.get("raceName", "Grand Prix")
            circuit = race.get("Circuit", {}).get("circuitName", "")
            race_date = race.get("date", "")
            time_str = race.get("time", "")[:5] if race.get("time") else None
            # Verificar si hay piloto ARG en la grilla — siempre true si Colapinto sigue en F1
            return NormalizedMatch(
                id=f"motorsport-f1-{re.sub(chr(32), '-', name.lower())[:30]}",
                sport="motorsport",
                source="ergast",
                competition="Fórmula 1",
                home_team=name,
                away_team=circuit,
                status="upcoming",
                start_time_arg=time_str,
                argentina_relevance="jugador_arg",
                argentina_team="Franco Colapinto",
                raw=race,
            )
        except Exception:
            return None

    def _session_to_match(self, session: dict) -> NormalizedMatch | None:
        try:
            session_name = session.get("session_name", "Sesión")
            gp_name = session.get("meeting_name", "Grand Prix")
            return NormalizedMatch(
                id=f"motorsport-openf1-{session.get('session_key','0')}",
                sport="motorsport",
                source="openf1",
                competition=f"F1 — {gp_name}",
                home_team=session_name,
                away_team=session.get("circuit_short_name", ""),
                status="live",
                argentina_relevance="jugador_arg",
                argentina_team="Franco Colapinto",
                raw=session,
            )
        except Exception:
            return None
