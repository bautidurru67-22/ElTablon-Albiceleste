"""
Adapter automovilismo — OpenF1 API (real, gratuita) + Sofascore.

OpenF1 es la única API gratuita y oficial para F1 en tiempo real.
https://openf1.org/
"""
import logging
from datetime import date, datetime, timezone
from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch
from scraping.sources import sofascore
from scraping.normalizers import sofascore_normalizer

logger = logging.getLogger(__name__)

OPENF1_SESSIONS = "https://api.openf1.org/v1/sessions?year={year}&date_start>={date}"
ERGAST_CURRENT  = "https://ergast.com/api/f1/current.json"


class MotorsportAdapter(BaseScraper):

    async def scrape(self) -> list[NormalizedMatch]:
        matches = []

        # ── 1. OpenF1 API — sesiones actuales ─────────────────────────────
        try:
            today = date.today()
            url = f"https://api.openf1.org/v1/sessions?year={today.year}&date_start>={today.isoformat()}"
            sessions = await self.fetch_json(url)
            if isinstance(sessions, list):
                for s in sessions[:3]:  # máximo 3 sesiones hoy
                    start = s.get("date_start", "")
                    end   = s.get("date_end", "")
                    name  = s.get("session_name", "Grand Prix")
                    location = s.get("location", "")
                    country  = s.get("country_name", "")
                    circuit  = f"{location}, {country}".strip(", ")
                    gp_name  = s.get("meeting_name", name)
                    full_name = f"F1 — {gp_name} · {name}"

                    status = "upcoming"
                    try:
                        dt_start = datetime.fromisoformat(start.replace("Z", "+00:00"))
                        dt_end   = datetime.fromisoformat(end.replace("Z", "+00:00"))
                        now = datetime.now(tz=timezone.utc)
                        if dt_start <= now <= dt_end:
                            status = "live"
                        elif now > dt_end:
                            status = "finished"
                        arg_h = (dt_start.hour - 3) % 24
                        start_time_arg = f"{arg_h:02d}:{dt_start.minute:02d}"
                    except Exception:
                        start_time_arg = None

                    matches.append(NormalizedMatch(
                        id=f"motorsport-f1-{s.get('session_key', 'x')}",
                        sport="motorsport", source="openf1",
                        competition="Fórmula 1",
                        home_team=gp_name,
                        away_team=circuit,
                        status=status,
                        start_time_arg=start_time_arg,
                        argentina_relevance="jugador_arg",
                        argentina_team="Franco Colapinto",
                        broadcast="ESPN Premium",
                        raw=s,
                    ))
            logger.info(f"[motorsport/openf1] {len(matches)} sesiones F1")
        except Exception as e:
            logger.warning(f"[motorsport/openf1] {e}")

        # ── 2. Ergast F1 calendario (si OpenF1 vacío) ─────────────────────
        if not matches:
            try:
                data = await self.fetch_json(ERGAST_CURRENT)
                races = data.get("MRData", {}).get("RaceTable", {}).get("Races", [])
                today = date.today()
                for race in races:
                    rd = race.get("date", "")
                    if not rd:
                        continue
                    race_date = date.fromisoformat(rd)
                    if abs((race_date - today).days) <= 2:
                        name = race.get("raceName", "Grand Prix")
                        circuit = race.get("Circuit", {}).get("circuitName", "")
                        start_time = race.get("time", "")
                        arg_h_str = None
                        if start_time:
                            try:
                                h = int(start_time[:2])
                                m = int(start_time[3:5])
                                arg_h_str = f"{(h-3)%24:02d}:{m:02d}"
                            except Exception:
                                pass
                        status = "finished" if race_date < today else "upcoming"
                        matches.append(NormalizedMatch(
                            id=f"motorsport-f1-ergast-{rd}",
                            sport="motorsport", source="ergast",
                            competition="Fórmula 1",
                            home_team=name, away_team=circuit,
                            status=status,
                            start_time_arg=arg_h_str,
                            argentina_relevance="jugador_arg",
                            argentina_team="Franco Colapinto",
                            broadcast="ESPN Premium",
                            raw=race,
                        ))
                logger.info(f"[motorsport/ergast] {len(matches)} carreras F1")
            except Exception as e:
                logger.warning(f"[motorsport/ergast] {e}")

        # ── 3. Sofascore (Turismo Carretera, TC2000, etc.) ─────────────────
        try:
            data = await sofascore.get_events_by_date("motorsport")
            events = data.get("events", [])
            ss = sofascore_normalizer.normalize_events(events, "motorsport")
            existing = {m.id for m in matches}
            new = [m for m in ss if m.id not in existing]
            logger.info(f"[motorsport/sofascore] {len(new)} con ARG")
            matches.extend(new)
        except Exception as e:
            logger.warning(f"[motorsport/sofascore] {e}")

        logger.info(f"[motorsport] TOTAL {len(matches)}")
        return matches
