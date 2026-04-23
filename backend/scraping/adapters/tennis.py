"""
Tenis argentino.
1. ESPN API — ATP/WTA scoreboard (no key)
2. ATP Live JSON — endpoint interno ATP
3. TheSportsDB — ATP events
4. Sofascore — fallback
"""
import logging, re
from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch
from scraping.argentina import normalize_str, ARG_PLAYERS
from scraping.sources.espn_api import get_sport_events, parse_event as parse_espn
from scraping.sources.atp_live import get_live_scores
from scraping.sources.thesportsdb import get_events_today, parse_event as parse_tsdb
from scraping.sources.sofascore_safe import get_events_by_date as ss_today, get_live_events as ss_live
from scraping.normalizers import sofascore_normalizer

logger = logging.getLogger(__name__)
SPORT = "tenis"
ARG_LOWER = {normalize_str(k) for k in ARG_PLAYERS.keys()}

def _is_arg(name: str) -> bool:
    n = normalize_str(name)
    return any(a in n for a in ARG_LOWER)

def _make(home: str, away: str, comp: str, status: str,
          raw: dict, src: str) -> NormalizedMatch | None:
    if not home or not away:
        return None
    if not _is_arg(home) and not _is_arg(away):
        return None
    arg_team = home if _is_arg(home) else away
    hn = re.sub(r"\W+", "-", normalize_str(home))[:20]
    an = re.sub(r"\W+", "-", normalize_str(away))[:20]
    return NormalizedMatch(
        id=f"{SPORT}-{src}-{hn}-{an}", sport=SPORT, source=src,
        competition=comp or "ATP Tour",
        home_team=home, away_team=away,
        home_score=raw.get("home_score"), away_score=raw.get("away_score"),
        score_detail=raw.get("score_detail", ""),
        status=status, minute=raw.get("minute"),
        start_time_arg=raw.get("start_time"),
        argentina_relevance="jugador_arg", argentina_team=arg_team,
        broadcast=raw.get("broadcast"), raw=raw,
    )

class TennisAdapter(BaseScraper):
    async def scrape(self) -> list[NormalizedMatch]:
        matches: list[NormalizedMatch] = []
        seen: set[str] = set()
        def add(m):
            if m and m.id not in seen:
                seen.add(m.id); matches.append(m)

        # 1. ESPN ATP/WTA
        try:
            events = await get_sport_events(SPORT)
            before = len(matches)
            for ev in events:
                raw = parse_espn(ev)
                if raw:
                    add(_make(raw.get("home",""), raw.get("away",""),
                              raw.get("competition",""), raw.get("status","upcoming"),
                              raw, "espn"))
            logger.info(f"[tennis/espn] {len(matches) - before}")
        except Exception as e:
            logger.warning(f"[tennis/espn] {e}")

        # 2. ATP Live JSON
        try:
            atp = await get_live_scores()
            before = len(matches)
            for raw in atp:
                add(_make(raw.get("home",""), raw.get("away",""),
                          raw.get("competition",""), raw.get("status","upcoming"),
                          raw, "atptour"))
            logger.info(f"[tennis/atptour] {len(matches) - before}")
        except Exception as e:
            logger.warning(f"[tennis/atptour] {e}")

        # 3. Sofascore fallback
        if not matches:
            try:
                for fn in [ss_today, ss_live]:
                    data = await fn(SPORT)
                    for m in sofascore_normalizer.normalize_events(
                            data.get("events", []), SPORT):
                        if m.id not in seen:
                            seen.add(m.id); matches.append(m)
                logger.info(f"[tennis/sofascore] {len(matches)}")
            except Exception as e:
                logger.warning(f"[tennis/sofascore] {e}")

        logger.info(f"[tennis] TOTAL {len(matches)}")
        return matches
