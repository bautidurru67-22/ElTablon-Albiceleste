"""
Básquet argentino.

Fuentes:
1. NBA API oficial (cdn.nba.com) — gratis, sin key, JSON real
2. TheSportsDB               — LNB argentina + FIBA
3. Sofascore                 — fallback
"""
import logging
import re
from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch
from scraping.argentina import detect_argentina_relevance, normalize_str
from scraping.sources.nba_official import get_today_scoreboard, parse_games
from scraping.sources.thesportsdb import get_events_today, parse_event
from scraping.sources.sofascore_safe import get_events_by_date as ss_today, get_live_events as ss_live
from scraping.normalizers import sofascore_normalizer

logger = logging.getLogger(__name__)

TSDB_BASKETBALL = {
    4387: "NBA",
    4966: "Liga Nacional de Básquet",
}


def _make_match(raw: dict, source: str) -> NormalizedMatch | None:
    home = raw.get("home", "").strip()
    away = raw.get("away", "").strip()
    if not home or not away:
        return None
    comp = raw.get("competition", "") or ""
    # NBA: arg_team viene del parser oficial
    arg_team = raw.get("arg_team")
    if arg_team:
        relevance = "jugador_arg"
    else:
        relevance, arg_team = detect_argentina_relevance(home, away, comp, "basquet")
    if relevance == "none":
        return None
    h_n = re.sub(r"\W+", "-", normalize_str(home))[:20]
    a_n = re.sub(r"\W+", "-", normalize_str(away))[:20]
    return NormalizedMatch(
        id=f"basquet-{source}-{h_n}-{a_n}",
        sport="basquet", source=source, competition=comp or "Básquet",
        home_team=home, away_team=away,
        home_score=raw.get("home_score"), away_score=raw.get("away_score"),
        status=raw.get("status", "upcoming"),
        minute=raw.get("minute"), start_time_arg=raw.get("start_time"),
        argentina_relevance=relevance, argentina_team=arg_team, raw=raw,
    )


class BasketballAdapter(BaseScraper):

    async def scrape(self) -> list[NormalizedMatch]:
        matches: list[NormalizedMatch] = []
        seen: set[str] = set()

        def _add(m: NormalizedMatch | None) -> None:
            if m and m.id not in seen:
                seen.add(m.id)
                matches.append(m)

        # ── 1. NBA API oficial ────────────────────────────────────────────
        try:
            data = await get_today_scoreboard()
            for raw in parse_games(data):
                _add(_make_match(raw, "nba"))
            logger.info(f"[basketball/nba] {len(matches)}")
        except Exception as e:
            logger.warning(f"[basketball/nba] {e}")

        # ── 2. TheSportsDB (LNB argentina) ────────────────────────────────
        try:
            before = len(matches)
            for lid, lname in TSDB_BASKETBALL.items():
                events = await get_events_today(lid)
                for ev in events:
                    raw = parse_event(ev, "basquet")
                    raw["competition"] = raw.get("competition") or lname
                    _add(_make_match(raw, "tsdb"))
            logger.info(f"[basketball/tsdb] {len(matches) - before}")
        except Exception as e:
            logger.warning(f"[basketball/thesportsdb] {e}")

        # ── 3. Sofascore fallback ─────────────────────────────────────────
        if not matches:
            try:
                for fn in [ss_today, ss_live]:
                    data = await fn("basquet")
                    ss = sofascore_normalizer.normalize_events(data.get("events", []), "basquet")
                    for m in ss:
                        if m.id not in seen:
                            seen.add(m.id)
                            matches.append(m)
                logger.info(f"[basketball/sofascore-fallback] {len(matches)}")
            except Exception as e:
                logger.warning(f"[basketball/sofascore] {e}")

        logger.info(f"[basketball] TOTAL {len(matches)}")
        return matches
