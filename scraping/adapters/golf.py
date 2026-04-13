"""Golf — ESPN API + TheSportsDB + Sofascore."""
import logging, re
from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch
from scraping.argentina import detect_argentina_relevance, normalize_str
from scraping.sources.espn_api import get_sport_events, parse_event as parse_espn
from scraping.sources.thesportsdb import get_events_today, get_next_events, parse_event as parse_tsdb
from scraping.sources.sofascore_safe import get_events_by_date as ss_today, get_live_events as ss_live
from scraping.normalizers import sofascore_normalizer
logger = logging.getLogger(__name__)
SPORT = "golf"
TSDB_GOLF = {4378: "PGA Tour", 4379: "European Tour"}

def _make(raw: dict, src: str) -> NormalizedMatch | None:
    h, a = raw.get("home","").strip(), raw.get("away","").strip()
    if not h or not a: return None
    comp = raw.get("competition","") or ""
    rel, arg = detect_argentina_relevance(h, a, comp, SPORT)
    if rel == "none": return None
    hn = re.sub(r"\W+","-",normalize_str(h))[:20]
    an = re.sub(r"\W+","-",normalize_str(a))[:20]
    return NormalizedMatch(id=f"{SPORT}-{src}-{hn}-{an}", sport=SPORT, source=src,
        competition=comp or "Golf", home_team=h, away_team=a,
        home_score=raw.get("home_score"), away_score=raw.get("away_score"),
        status=raw.get("status","upcoming"), start_time_arg=raw.get("start_time"),
        argentina_relevance=rel, argentina_team=arg, raw=raw)

class GolfAdapter(BaseScraper):
    async def scrape(self) -> list[NormalizedMatch]:
        matches, seen = [], set()
        def add(m):
            if m and m.id not in seen: seen.add(m.id); matches.append(m)
        try:
            for ev in await get_sport_events(SPORT):
                raw = parse_espn(ev)
                if raw: add(_make(raw, "espn"))
            logger.info(f"[golf/espn] {len(matches)}")
        except Exception as e: logger.warning(f"[golf/espn] {e}")
        try:
            before = len(matches)
            for lid, lname in TSDB_GOLF.items():
                for fn in [get_events_today, get_next_events]:
                    for ev in await fn(lid):
                        raw = parse_tsdb(ev, SPORT)
                        raw["competition"] = raw.get("competition") or lname
                        add(_make(raw, "tsdb"))
            logger.info(f"[golf/tsdb] {len(matches) - before}")
        except Exception as e: logger.warning(f"[golf/tsdb] {e}")
        if not matches:
            try:
                for fn in [ss_today, ss_live]:
                    data = await fn(SPORT)
                    for m in sofascore_normalizer.normalize_events(data.get("events",[]), SPORT):
                        if m.id not in seen: seen.add(m.id); matches.append(m)
            except Exception as e: logger.warning(f"[golf/sofascore] {e}")
        logger.info(f"[golf] TOTAL {len(matches)}"); return matches
