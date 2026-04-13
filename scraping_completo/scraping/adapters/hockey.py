"""
Hockey sobre césped argentino.

Fuentes:
1. FIH API JSON oficial     — Pro League, World Cup, Champions Trophy
2. TheSportsDB              — cobertura adicional
3. Sofascore                — fallback
"""
import logging
import re
from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch
from scraping.argentina import detect_argentina_relevance, normalize_str
from scraping.sources.fih_api import get_today_matches, parse_match as parse_fih
from scraping.sources.thesportsdb import get_events_today, parse_event
from scraping.sources.sofascore_safe import get_events_by_date as ss_today, get_live_events as ss_live
from scraping.normalizers import sofascore_normalizer

logger = logging.getLogger(__name__)

TSDB_HOCKEY = {5066: "FIH Pro League M", 5067: "FIH Pro League W"}


def _make_match(raw: dict, source: str) -> NormalizedMatch | None:
    home = raw.get("home", "").strip()
    away = raw.get("away", "").strip()
    if not home or not away:
        return None
    comp = raw.get("competition", "") or ""
    relevance, arg_team = detect_argentina_relevance(home, away, comp, "hockey")
    if relevance == "none":
        return None
    h_n = re.sub(r"\W+", "-", normalize_str(home))[:20]
    a_n = re.sub(r"\W+", "-", normalize_str(away))[:20]
    return NormalizedMatch(
        id=f"hockey-{source}-{h_n}-{a_n}",
        sport="hockey", source=source, competition=comp or "Hockey",
        home_team=home, away_team=away,
        home_score=raw.get("home_score"), away_score=raw.get("away_score"),
        status=raw.get("status", "upcoming"),
        minute=raw.get("minute"), start_time_arg=raw.get("start_time"),
        argentina_relevance=relevance, argentina_team=arg_team, raw=raw,
    )


class HockeyAdapter(BaseScraper):

    async def scrape(self) -> list[NormalizedMatch]:
        matches: list[NormalizedMatch] = []
        seen: set[str] = set()

        def _add(m: NormalizedMatch | None) -> None:
            if m and m.id not in seen:
                seen.add(m.id)
                matches.append(m)

        # ── 1. FIH API oficial ────────────────────────────────────────────
        try:
            fih_raw = await get_today_matches()
            for raw_m in fih_raw:
                raw = parse_fih(raw_m)
                if raw:
                    _add(_make_match(raw, "fih"))
            logger.info(f"[hockey/fih] {len(matches)}")
        except Exception as e:
            logger.warning(f"[hockey/fih] {e}")

        # ── 2. TheSportsDB ────────────────────────────────────────────────
        try:
            before = len(matches)
            for lid, lname in TSDB_HOCKEY.items():
                events = await get_events_today(lid)
                for ev in events:
                    raw = parse_event(ev, "hockey")
                    raw["competition"] = raw.get("competition") or lname
                    _add(_make_match(raw, "tsdb"))
            logger.info(f"[hockey/tsdb] {len(matches) - before}")
        except Exception as e:
            logger.warning(f"[hockey/thesportsdb] {e}")

        # ── 3. Sofascore fallback ─────────────────────────────────────────
        if not matches:
            try:
                for fn in [ss_today, ss_live]:
                    data = await fn("hockey")
                    ss = sofascore_normalizer.normalize_events(data.get("events", []), "hockey")
                    for m in ss:
                        if m.id not in seen:
                            seen.add(m.id)
                            matches.append(m)
                logger.info(f"[hockey/sofascore-fallback] {len(matches)}")
            except Exception as e:
                logger.warning(f"[hockey/sofascore] {e}")

        logger.info(f"[hockey] TOTAL {len(matches)}")
        return matches
