"""
Básquet argentino.
1. ESPN API — NBA (no key, funciona desde Railway)
2. NBA API oficial — cdn.nba.com (backup ESPN)
3. TheSportsDB — LNB argentina
4. Sofascore — fallback
"""
import logging
import re
from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch
from scraping.argentina import detect_argentina_relevance, normalize_str
from scraping.sources.espn_api import get_sport_events, parse_event as parse_espn
from scraping.sources.nba_official import get_today_scoreboard, parse_games
from scraping.sources.thesportsdb import get_events_today, get_next_events, parse_event as parse_tsdb
from scraping.sources.sofascore_safe import get_events_by_date as ss_today, get_live_events as ss_live
from scraping.normalizers import sofascore_normalizer

logger = logging.getLogger(__name__)
SPORT = "basquet"
TSDB_BASQUET = {4966: "Liga Nacional de Básquet"}


def _make(raw: dict, src: str) -> NormalizedMatch | None:
    home = raw.get("home", "").strip()
    away = raw.get("away", "").strip()
    if not home or not away:
        return None
    comp = raw.get("competition", "") or ""
    arg_team = raw.get("arg_team")
    if arg_team:
        rel = "jugador_arg"
    else:
        rel, arg_team = detect_argentina_relevance(home, away, comp, SPORT)
    if rel == "none":
        return None
    hn = re.sub(r"\W+", "-", normalize_str(home))[:20]
    an = re.sub(r"\W+", "-", normalize_str(away))[:20]
    return NormalizedMatch(
        id=f"{SPORT}-{src}-{hn}-{an}", sport=SPORT, source=src,
        competition=comp or "Básquet",
        home_team=home, away_team=away,
        home_score=raw.get("home_score"), away_score=raw.get("away_score"),
        status=raw.get("status", "upcoming"), minute=raw.get("minute"),
        start_time_arg=raw.get("start_time"),
        argentina_relevance=rel, argentina_team=arg_team,
        broadcast=raw.get("broadcast"), raw=raw,
    )


class BasketballAdapter(BaseScraper):
    async def scrape(self) -> list[NormalizedMatch]:
        matches: list[NormalizedMatch] = []
        seen: set[str] = set()

        def add(m):
            if m and m.id not in seen:
                seen.add(m.id); matches.append(m)

        # 1. ESPN NBA
        try:
            events = await get_sport_events(SPORT)
            before = len(matches)
            for ev in events:
                raw = parse_espn(ev)
                if raw:
                    add(_make(raw, "espn"))
            logger.info(f"[basketball/espn] {len(matches) - before}")
        except Exception as e:
            logger.warning(f"[basketball/espn] {e}")

        # 2. NBA API oficial (backup)
        try:
            data = await get_today_scoreboard()
            before = len(matches)
            for raw in parse_games(data):
                add(_make(raw, "nba"))
            logger.info(f"[basketball/nba] {len(matches) - before}")
        except Exception as e:
            logger.warning(f"[basketball/nba] {e}")

        # 3. TheSportsDB LNB
        try:
            before = len(matches)
            for lid, lname in TSDB_BASQUET.items():
                for fn in [get_events_today, get_next_events]:
                    for ev in await fn(lid):
                        raw = parse_tsdb(ev, SPORT)
                        raw["competition"] = raw.get("competition") or lname
                        add(_make(raw, "tsdb"))
            logger.info(f"[basketball/tsdb] {len(matches) - before}")
        except Exception as e:
            logger.warning(f"[basketball/tsdb] {e}")

        # 4. Sofascore fallback
        if not matches:
            try:
                for fn in [ss_today, ss_live]:
                    data = await fn(SPORT)
                    for m in sofascore_normalizer.normalize_events(
                            data.get("events", []), SPORT):
                        if m.id not in seen:
                            seen.add(m.id); matches.append(m)
                logger.info(f"[basketball/sofascore] {len(matches)}")
            except Exception as e:
                logger.warning(f"[basketball/sofascore] {e}")

        logger.info(f"[basketball] TOTAL {len(matches)}")
        return matches
