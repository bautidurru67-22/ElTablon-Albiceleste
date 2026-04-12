"""
Adapter básquet argentino.

Jerarquía:
1. NBA API oficial (cdn.nba.com) — gratis, sin key
2. LNB.com.ar HTML — Liga Nacional argentina
3. CABB.com.ar — selección argentina
4. Latinbasket.com — cobertura sudamericana
5. Sofascore — Euroliga, ACB, FIBA
"""
import logging
import re
from datetime import date, datetime, timezone
from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch
from scraping.sources import sofascore
from scraping.sources.cabb import get_lnb_html, get_cabb_html, parse_lnb
from scraping.normalizers import sofascore_normalizer
from scraping.argentina import detect_argentina_relevance, normalize_str, ARG_PLAYERS

logger = logging.getLogger(__name__)

NBA_SCOREBOARD = "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json"

ARG_NBA_PLAYERS_NORM = {
    "campazzo", "facundo campazzo", "bolmaro", "leandro bolmaro",
    "laprovittola", "nicolas laprovittola", "vildoza", "luca vildoza",
    "deck", "gabriel deck", "brussino", "nicolas brussino",
}


class BasketballAdapter(BaseScraper):

    async def scrape(self) -> list[NormalizedMatch]:
        matches: list[NormalizedMatch] = []

        # ── 1. NBA API oficial ─────────────────────────────────────────────
        try:
            data = await self.fetch_json(NBA_SCOREBOARD)
            games = data.get("scoreboard", {}).get("games", [])
            nba = self._parse_nba(games)
            logger.info(f"[basketball/nba] {len(nba)} ARG de {len(games)} total")
            matches.extend(nba)
        except Exception as e:
            logger.warning(f"[basketball/nba] {e}")

        # ── 2. LNB.com.ar HTML ────────────────────────────────────────────
        try:
            html = await get_lnb_html()
            if html:
                raws = parse_lnb(html)
                existing = {m.id for m in matches}
                for raw in raws:
                    home, away = raw.get("home", ""), raw.get("away", "")
                    if not home or not away:
                        continue
                    comp = raw.get("competition", "Liga Nacional de Básquet")
                    relevance, arg_team = detect_argentina_relevance(home, away, comp, "basquet")
                    if relevance == "none":
                        continue
                    h_n = re.sub(r"\W+", "-", normalize_str(home))[:20]
                    a_n = re.sub(r"\W+", "-", normalize_str(away))[:20]
                    mid = f"basquet-lnb-{h_n}-{a_n}"
                    if mid not in existing:
                        existing.add(mid)
                        matches.append(NormalizedMatch(
                            id=mid, sport="basquet", source="lnb",
                            competition=comp, home_team=home, away_team=away,
                            home_score=raw.get("home_score"),
                            away_score=raw.get("away_score"),
                            status=raw.get("status", "upcoming"),
                            start_time_arg=raw.get("start_time"),
                            argentina_relevance=relevance, argentina_team=arg_team, raw=raw,
                        ))
                logger.info(f"[basketball/lnb] {len(raws)} raws procesados")
        except Exception as e:
            logger.warning(f"[basketball/lnb] {e}")

        # ── 3. Sofascore scheduled ─────────────────────────────────────────
        try:
            data = await sofascore.get_events_by_date("basquet")
            events = data.get("events", [])
            ss = sofascore_normalizer.normalize_events(events, "basquet")
            existing = {m.id for m in matches}
            new = [m for m in ss if m.id not in existing]
            logger.info(f"[basketball/ss-sched] {len(new)}")
            matches.extend(new)
        except Exception as e:
            logger.warning(f"[basketball/ss-sched] {e}")

        # ── 4. Sofascore live ──────────────────────────────────────────────
        try:
            data = await sofascore.get_live_events("basquet")
            events = data.get("events", [])
            live = sofascore_normalizer.normalize_events(events, "basquet")
            existing = {m.id for m in matches}
            new = [m for m in live if m.id not in existing]
            logger.info(f"[basketball/ss-live] {len(new)}")
            matches.extend(new)
        except Exception as e:
            logger.warning(f"[basketball/ss-live] {e}")

        logger.info(f"[basketball] TOTAL {len(matches)}")
        return matches

    def _parse_nba(self, games: list[dict]) -> list[NormalizedMatch]:
        results = []
        for g in games:
            home = g.get("homeTeam", {})
            away = g.get("awayTeam", {})
            home_full = f"{home.get('teamCity','')} {home.get('teamName','')}".strip()
            away_full = f"{away.get('teamCity','')} {away.get('teamName','')}".strip()

            home_arg = self._has_arg_player(home)
            away_arg = self._has_arg_player(away)
            if not home_arg and not away_arg:
                continue

            gs = g.get("gameStatus", 1)
            status = "upcoming" if gs == 1 else ("live" if gs == 2 else "finished")

            hs = as_ = None
            try:
                if gs in (2, 3):
                    hs = int(home.get("score", 0))
                    as_ = int(away.get("score", 0))
            except (ValueError, TypeError):
                pass

            period = g.get("period", 0)
            clock  = g.get("gameClock", "")
            minute = f"C{period} {clock}".strip() if status == "live" else None

            start = g.get("gameTimeUTC", "")
            start_time_arg = None
            if start:
                try:
                    dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                    start_time_arg = f"{(dt.hour-3)%24:02d}:{dt.minute:02d}"
                except Exception:
                    pass

            results.append(NormalizedMatch(
                id=f"basquet-nba-{g.get('gameId','x')}",
                sport="basquet", source="nba", competition="NBA",
                home_team=home_full, away_team=away_full,
                home_score=hs, away_score=as_,
                status=status, minute=minute,
                start_time_arg=start_time_arg,
                argentina_relevance="jugador_arg",
                argentina_team=home_full if home_arg else away_full,
                broadcast="NBA TV", raw=g,
            ))
        return results

    def _has_arg_player(self, team: dict) -> bool:
        for p in team.get("players", []):
            name = normalize_str(p.get("name", p.get("familyName", "")))
            for arg_n in ARG_NBA_PLAYERS_NORM:
                if arg_n in name:
                    return True
        return False
