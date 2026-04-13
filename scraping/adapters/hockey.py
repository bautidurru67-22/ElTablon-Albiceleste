"""Hockey — FIH API + TheSportsDB + Sofascore."""
import logging, re
from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch
from scraping.argentina import detect_argentina_relevance, normalize_str
from scraping.sources.fih_api import get_today_matches, parse_match as parse_fih
from scraping.sources.thesportsdb import get_events_today, get_next_events, parse_event as parse_tsdb
from scraping.sources.sofascore_safe import get_events_by_date as ss_today, get_live_events as ss_live
from scraping.normalizers import sofascore_normalizer
logger = logging.getLogger(__name__)
SPORT = "hockey"
TSDB_HOCKEY = {5066: "FIH Pro League"}

def _make(raw: dict, src: str) -> NormalizedMatch | None:
    h, a = raw.get("home","").strip(), raw.get("away","").strip()
    if not h or not a: return None
    comp = raw.get("competition","") or ""
    rel, arg = detect_argentina_relevance(h, a, comp, SPORT)
    if rel == "none": return None
    hn = re.sub(r"\W+","-",normalize_str(h))[:20]
    an = re.sub(r"\W+","-",normalize_str(a))[:20]
    return NormalizedMatch(id=f"{SPORT}-{src}-{hn}-{an}", sport=SPORT, source=src,
        competition=comp or "Hockey", home_team=h, away_team=a,
        home_score=raw.get("home_score"), away_score=raw.get("away_score"),
        status=raw.get("status","upcoming"), start_time_arg=raw.get("start_time"),
        argentina_relevance=rel, argentina_team=arg, raw=raw)

class HockeyAdapter(BaseScraper):
    async def scrape(self) -> list[NormalizedMatch]:
        matches, seen = [], set()
        def add(m):
            if m and m.id not in seen: seen.add(m.id); matches.append(m)
        try:
            for raw_m in await get_today_matches():
                raw = parse_fih(raw_m)
                if raw: add(_make(raw, "fih"))
            logger.info(f"[hockey/fih] {len(matches)}")
        except Exception as e: logger.warning(f"[hockey/fih] {e}")
        try:
            before = len(matches)
            for lid, lname in TSDB_HOCKEY.items():
                for fn in [get_events_today, get_next_events]:
                    for ev in await fn(lid):
                        raw = parse_tsdb(ev, SPORT)
                        raw["competition"] = raw.get("competition") or lname
                        add(_make(raw, "tsdb"))
            logger.info(f"[hockey/tsdb] {len(matches) - before}")
        except Exception as e: logger.warning(f"[hockey/tsdb] {e}")
        if not matches:
            try:
                for fn in [ss_today, ss_live]:
                    data = await fn(SPORT)
                    for m in sofascore_normalizer.normalize_events(data.get("events",[]), SPORT):
                        if m.id not in seen: seen.add(m.id); matches.append(m)
                logger.info(f"[hockey/sofascore] {len(matches)}")
            except Exception as e: logger.warning(f"[hockey/sofascore] {e}")
        logger.info(f"[hockey] TOTAL {len(matches)}"); return matches
