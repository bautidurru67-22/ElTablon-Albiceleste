"""Vóley — TheSportsDB (FIVB) + Sofascore."""
import logging, re
from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch
from scraping.argentina import detect_argentina_relevance, normalize_str
from scraping.sources.thesportsdb import get_events_today, get_next_events, parse_event as parse_tsdb
from scraping.sources.sofascore_safe import get_events_by_date as ss_today, get_live_events as ss_live
from scraping.normalizers import sofascore_normalizer
logger = logging.getLogger(__name__)
SPORT = "voley"

def _make(raw, src):
    h, a = raw.get("home","").strip(), raw.get("away","").strip()
    if not h or not a: return None
    comp = raw.get("competition","") or ""
    rel, arg = detect_argentina_relevance(h, a, comp, SPORT)
    if rel == "none": return None
    hn = re.sub(r"\W+","-",normalize_str(h))[:20]
    an = re.sub(r"\W+","-",normalize_str(a))[:20]
    return NormalizedMatch(id=f"{SPORT}-{src}-{hn}-{an}", sport=SPORT, source=src,
        competition=comp or "Vóley", home_team=h, away_team=a,
        home_score=raw.get("home_score"), away_score=raw.get("away_score"),
        status=raw.get("status","upcoming"), start_time_arg=raw.get("start_time"),
        argentina_relevance=rel, argentina_team=arg, raw=raw)

class VolleyballAdapter(BaseScraper):
    async def scrape(self):
        matches, seen = [], set()
        def add(m):
            if m and m.id not in seen: seen.add(m.id); matches.append(m)
        try:
            for fn in [get_events_today, get_next_events]:
                for ev in await fn(5028):  # FIVB
                    raw = parse_tsdb(ev, SPORT); add(_make(raw, "tsdb"))
            logger.info(f"[voley/tsdb] {len(matches)}")
        except Exception as e: logger.warning(f"[voley/tsdb] {e}")
        if not matches:
            try:
                for fn in [ss_today, ss_live]:
                    data = await fn(SPORT)
                    for m in sofascore_normalizer.normalize_events(data.get("events",[]), SPORT):
                        if m.id not in seen: seen.add(m.id); matches.append(m)
            except Exception as e: logger.warning(f"[voley/sofascore] {e}")
        logger.info(f"[voley] TOTAL {len(matches)}"); return matches
