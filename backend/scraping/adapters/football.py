"""
Fútbol argentino robusto.
Prioridad de fuentes:
1) Promiedos (local ARG)
2) AFA (oficial local)
3) API-Football (si hay key)
4) Sofascore
5) ESPN scoreboard open API (fallback final)
"""
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch
from scraping.sources.promiedos import get_today_html, parse_matches
from scraping.sources.afa import get_fixture_html, parse_fixture
from scraping.sources.api_football import get_fixtures_today, parse_fixture as parse_api_football
from scraping.normalizers.promiedos_normalizer import normalize_matches as normalize_promiedos
from scraping.sources.sofascore import get_events_by_date, get_live_events
from scraping.normalizers import sofascore_normalizer
from scraping.argentina import detect_argentina_relevance, normalize_str, ARG_CLUBS

logger = logging.getLogger(__name__)


class FootballAdapter(BaseScraper):
    SOURCE_ORDER = ["promiedos", "afa", "api_football", "sofascore", "espn"]
    DIAG_VERSION = "football-diag-v5-2026-04-13"
    LAST_RUN: dict = {}
    ARG_COMP_KEYWORDS = [
        "liga profesional", "primera nacional", "primera b", "primera c",
        "primera d", "federal a", "copa argentina", "copa de la liga",
        "supercopa argentina", "torneo argentina", "conmebol libertadores",
        "conmebol sudamericana", "seleccion argentina",
    ]
    NOISE_KEYWORDS = ["reserve", "reserves", "u20", "u21", "u23"]

    async def scrape(self) -> list[NormalizedMatch]:
        matches: list[NormalizedMatch] = []
        seen: set[str] = set()
        diagnostics = {
            "diag_version": self.DIAG_VERSION,
            "sources": {},
            "total_unique": 0,
        }

        def add(m: NormalizedMatch | None):
            if m and self._is_editorial_match(m) and m.id not in seen:
                seen.add(m.id)
                matches.append(m)

        def record(source: str, raw_count: int = 0, added_count: int = 0, error: str | None = None):
            diagnostics["sources"][source] = {
                "raw_count": raw_count,
                "added_count": added_count,
                "error": error,
            }

        # 1) Promiedos: fuerte para Liga Profesional / Argentina
        try:
            html = await get_today_html()
            raw = parse_matches(html)
            before = len(matches)
            for m in normalize_promiedos(raw):
                add(m)
            added = len(matches) - before
            record("promiedos", raw_count=len(raw), added_count=added)
            logger.info(f"[football/promiedos] +{added} ({len(raw)} raw)")
        except Exception as e:
            record("promiedos", error=str(e))
            logger.warning(f"[football/promiedos] {e}")

        # 2) AFA oficial (fallback 1)
        if not matches:
            try:
                html = await get_fixture_html()
                raw = parse_fixture(html or "")
                before = len(matches)
                for m in normalize_promiedos(raw):
                    add(m)
                added = len(matches) - before
                record("afa", raw_count=len(raw), added_count=added)
                logger.info(f"[football/afa] +{added} ({len(raw)} raw)")
            except Exception as e:
                record("afa", error=str(e))
                logger.warning(f"[football/afa] {e}")

        # 3) API-Football
        try:
            raw = await get_fixtures_today()
            before = len(matches)
            for f in raw:
                parsed = parse_api_football(f)
                if not parsed:
                    continue
                rel, arg_team = detect_argentina_relevance(
                    parsed.get("home", ""),
                    parsed.get("away", ""),
                    parsed.get("competition", ""),
                    "futbol",
                )
                if rel == "none":
                    continue
                add(NormalizedMatch(
                    id=f"futbol-api-football-{normalize_str(parsed.get('home',''))[:16]}-{normalize_str(parsed.get('away',''))[:16]}",
                    sport="futbol",
                    source="api_football",
                    competition=parsed.get("competition") or "Fútbol",
                    home_team=parsed.get("home", ""),
                    away_team=parsed.get("away", ""),
                    home_score=parsed.get("home_score"),
                    away_score=parsed.get("away_score"),
                    status=parsed.get("status", "upcoming"),
                    minute=parsed.get("minute"),
                    start_time_arg=parsed.get("start_time"),
                    argentina_relevance=rel,
                    argentina_team=arg_team,
                    broadcast=parsed.get("broadcast"),
                    raw=parsed,
                ))
            added = len(matches) - before
            record("api_football", raw_count=len(raw), added_count=added)
            logger.info(f"[football/api_football] +{added} ({len(raw)} raw)")
        except Exception as e:
            record("api_football", error=str(e))
            logger.warning(f"[football/api_football] {e}")

        # 4) Sofascore
        try:
            before = len(matches)
            raw_total = 0
            for fn in [get_events_by_date, get_live_events]:
                data = await fn("futbol")
                events = data.get("events", [])
                raw_total += len(events)
                for m in sofascore_normalizer.normalize_events(events, "futbol"):
                    add(m)
            added = len(matches) - before
            record("sofascore", raw_count=raw_total, added_count=added)
            logger.info(f"[football/sofascore] +{added}")
        except Exception as e:
            record("sofascore", error=str(e))
            logger.warning(f"[football/sofascore] {e}")

        # 5) ESPN open API fallback final
        try:
            before = len(matches)
            espn_raw = await self._fetch_espn_events()
            for ev in espn_raw:
                nm = self._normalize_espn(ev)
                add(nm)
            added = len(matches) - before
            record("espn", raw_count=len(espn_raw), added_count=added)
            logger.info(f"[football/espn] +{added} ({len(espn_raw)} raw)")
        except Exception as e:
            record("espn", error=str(e))
            logger.warning(f"[football/espn] {e}")

        diagnostics["total_unique"] = len(matches)
        FootballAdapter.LAST_RUN = diagnostics
        logger.info(f"[football] TOTAL={len(matches)}")
        return matches

    async def _fetch_espn_events(self) -> list[dict]:
        date_yyyymmdd = datetime.now(ZoneInfo("America/Argentina/Buenos_Aires")).strftime("%Y%m%d")
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard?dates={date_yyyymmdd}"
        async with httpx.AsyncClient(timeout=httpx.Timeout(12.0, connect=6.0), follow_redirects=True) as client:
            r = await client.get(url, headers={"User-Agent": "tablon-scraper/1.0"})
            r.raise_for_status()
            data = r.json()
            return data.get("events", [])

    def _normalize_espn(self, ev: dict) -> NormalizedMatch | None:
        comp = ((ev.get("competitions") or [{}])[0]).get("competition", {}).get("name", "Fútbol")
        comp_data = (ev.get("competitions") or [{}])[0]
        competitors = comp_data.get("competitors", [])
        if len(competitors) < 2:
            return None

        home_obj = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
        away_obj = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])
        home = home_obj.get("team", {}).get("displayName", "")
        away = away_obj.get("team", {}).get("displayName", "")
        if not home or not away:
            return None

        rel, arg_team = detect_argentina_relevance(home, away, comp, "futbol")
        if rel == "none":
            return None

        status_type = ((comp_data.get("status") or {}).get("type") or {})
        state = status_type.get("state", "pre")
        detail = (status_type.get("shortDetail") or "").strip()
        if state == "in":
            status = "live"
        elif state == "post":
            status = "finished"
        else:
            status = "upcoming"

        def parse_score(c: dict):
            s = c.get("score")
            try:
                return int(s) if s not in (None, "") else None
            except Exception:
                return None

        minute = detail if status == "live" else None
        eid = ev.get("id") or f"{normalize_str(home)}-{normalize_str(away)}"
        return NormalizedMatch(
            id=f"futbol-espn-{eid}",
            sport="futbol",
            source="espn",
            competition=comp,
            home_team=home,
            away_team=away,
            home_score=parse_score(home_obj),
            away_score=parse_score(away_obj),
            status=status,
            minute=minute,
            start_time_arg=None,
            argentina_relevance=rel,
            argentina_team=arg_team,
            broadcast=None,
            raw=ev,
        )

    def _is_editorial_match(self, m: NormalizedMatch) -> bool:
        comp = normalize_str(m.competition or "")
        home = normalize_str(m.home_team or "")
        away = normalize_str(m.away_team or "")
        rel = m.argentina_relevance or "none"

        # Selección: solo si aparece explícitamente ARG/Argentina
        if rel == "seleccion":
            if "argentina" in home or "argentina" in away or home == "arg" or away == "arg":
                return True
            return False

        # Club argentino: priorizar competencias locales/regionales
        if rel == "club_arg":
            # Regla principal: si detectó club argentino, incluir.
            # Esto abre cobertura para Primera Nacional/ascenso/copas
            # aunque la competencia no llegue normalizada.
            return True

            # (mantenido como referencia editorial, no ejecuta por el return anterior)
            if any(k in comp for k in self.ARG_COMP_KEYWORDS):
                return True
            # Si no coincide competencia, igual permitir si ambos son clubes argentinos
            home_arg = any(k in home for k in ARG_CLUBS.keys())
            away_arg = any(k in away for k in ARG_CLUBS.keys())
            if home_arg and away_arg:
                return True
            return False

        # Jugador argentino: permitir en exterior salvo torneos claramente de juveniles/reserva
        if rel == "jugador_arg":
            if any(k in comp for k in self.NOISE_KEYWORDS):
                return False
            return True

        return False
