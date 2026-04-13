"""
Automovilismo — F1 con OpenF1 API oficial + Ergast.
OpenF1: openf1.org — API gratuita, oficial, sin key.
Ergast: ergast.com — calendario F1, sin key.
"""
import logging
import re
from datetime import date, datetime, timezone, timedelta
from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch
from scraping.sources.openf1 import get_current_session, get_current_race_weekend

logger = logging.getLogger(__name__)

ARG_F1 = {"colapinto", "franco colapinto"}


class MotorsportAdapter(BaseScraper):

    async def scrape(self) -> list[NormalizedMatch]:
        matches: list[NormalizedMatch] = []

        # ── OpenF1 — sesiones activas ──────────────────────────────────────
        try:
            today = date.today()
            import httpx
            url = (f"https://api.openf1.org/v1/sessions"
                   f"?date_start>={(today - timedelta(days=1)).isoformat()}"
                   f"&date_start<={(today + timedelta(days=2)).isoformat()}")
            async with httpx.AsyncClient(timeout=12) as c:
                r = await c.get(url)
                r.raise_for_status()
                sessions = r.json()

            if not isinstance(sessions, list):
                sessions = []

            for s in sessions:
                start_str = s.get("date_start", "")
                end_str   = s.get("date_end", "")
                session_name = s.get("session_name", "Sesión")
                gp_name = s.get("meeting_name", "Grand Prix")
                circuit = s.get("circuit_short_name", s.get("location", ""))
                country = s.get("country_name", "")

                status = "upcoming"
                start_time_arg = None
                try:
                    dt_s = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                    dt_e = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
                    now = datetime.now(tz=timezone.utc)
                    if dt_s <= now <= dt_e:
                        status = "live"
                    elif now > dt_e:
                        status = "finished"
                    start_time_arg = f"{(dt_s.hour - 3) % 24:02d}:{dt_s.minute:02d}"
                except Exception:
                    pass

                mid = re.sub(r"\W+", "-", f"{gp_name}-{session_name}")[:40].lower()
                matches.append(NormalizedMatch(
                    id=f"motorsport-f1-{mid}",
                    sport="motorsport", source="openf1",
                    competition=f"F1 — {gp_name}",
                    home_team=session_name,
                    away_team=f"{circuit}, {country}".strip(", "),
                    status=status,
                    start_time_arg=start_time_arg,
                    argentina_relevance="jugador_arg",
                    argentina_team="Franco Colapinto",
                    broadcast="ESPN Premium",
                    raw=s,
                ))
            logger.info(f"[motorsport/openf1] {len(matches)} sesiones")
        except Exception as e:
            logger.warning(f"[motorsport/openf1] {e}")

        # ── Ergast fallback si no hay sesiones ────────────────────────────
        if not matches:
            try:
                import httpx
                year = date.today().year
                today = date.today()
                async with httpx.AsyncClient(timeout=12) as c:
                    r = await c.get(f"https://ergast.com/api/f1/{year}.json")
                    r.raise_for_status()
                    races = r.json().get("MRData", {}).get("RaceTable", {}).get("Races", [])
                for race in races:
                    rd = race.get("date", "")
                    try:
                        race_date = date.fromisoformat(rd)
                    except Exception:
                        continue
                    if abs((race_date - today).days) > 3:
                        continue
                    status = "finished" if race_date < today else "upcoming"
                    gp = race.get("raceName", "Grand Prix")
                    circuit = race.get("Circuit", {}).get("circuitName", "")
                    t = race.get("time", "")
                    start_time_arg = None
                    if t and ":" in t:
                        try:
                            h, m = int(t[:2]), int(t[3:5])
                            start_time_arg = f"{(h-3)%24:02d}:{m:02d}"
                        except Exception:
                            pass
                    matches.append(NormalizedMatch(
                        id=f"motorsport-ergast-{rd}",
                        sport="motorsport", source="ergast",
                        competition="Fórmula 1",
                        home_team=gp, away_team=circuit,
                        status=status, start_time_arg=start_time_arg,
                        argentina_relevance="jugador_arg",
                        argentina_team="Franco Colapinto",
                        broadcast="ESPN Premium", raw=race,
                    ))
                logger.info(f"[motorsport/ergast] {len(matches)}")
            except Exception as e:
                logger.warning(f"[motorsport/ergast] {e}")

        logger.info(f"[motorsport] TOTAL {len(matches)}")
        return matches
