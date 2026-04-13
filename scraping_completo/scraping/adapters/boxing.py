"""Boxeo argentino — TheSportsDB + Sofascore fallback."""
import logging, re
from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch
from scraping.argentina import detect_argentina_relevance, normalize_str
from scraping.sources.thesportsdb import get_events_today, parse_event
from scraping.sources.sofascore_safe import get_events_by_date as ss_today, get_live_events as ss_live
from scraping.normalizers import sofascore_normalizer
logger = logging.getLogger(__name__)
SPORT = "boxeo"

def _make(raw: dict, src: str) -> NormalizedMatch | None:
    h = raw.get("home", "").strip()
    a = raw.get("away", "").strip()
    if not h or not a:
        return None
    comp = raw.get("competition", "") or ""
    rel, arg = detect_argentina_relevance(h, a, comp, SPORT)
    if rel == "none":
        return None
    hn = re.sub(r"\W+", "-", normalize_str(h))[:20]
    an = re.sub(r"\W+", "-", normalize_str(a))[:20]
    return NormalizedMatch(
        id=f"{SPORT}-{src}-{hn}-{an}", sport=SPORT, source=src,
        competition=comp or "Boxeo",
        home_team=h, away_team=a,
        home_score=raw.get("home_score"), away_score=raw.get("away_score"),
        status=raw.get("status", "upcoming"), start_time_arg=raw.get("start_time"),
        argentina_relevance=rel, argentina_team=arg, raw=raw,
    )

class BoxingAdapter(BaseScraper):
    async def scrape(self) -> list[NormalizedMatch]:
        matches: list[NormalizedMatch] = []
        seen: set[str] = set()
        def add(m):
            if m and m.id not in seen:
                seen.add(m.id); matches.append(m)
        try:
            for ev in await get_events_today(4443):  # Boxing TheSportsDB
                raw = parse_event(ev, SPORT)
                add(_make(raw, "tsdb"))
            logger.info(f"[boxeo/tsdb] {len(matches)}")
        except Exception as e:
            logger.warning(f"[boxeo/tsdb] {e}")
        if not matches:
            try:
                for fn in [ss_today, ss_live]:
                    data = await fn(SPORT)
                    for m in sofascore_normalizer.normalize_events(data.get("events", []), SPORT):
                        if m.id not in seen:
                            seen.add(m.id); matches.append(m)
                logger.info(f"[boxeo/sofascore] {len(matches)}")
            except Exception as e:
                logger.warning(f"[boxeo/sofascore] {e}")
        logger.info(f"[boxeo] TOTAL {len(matches)}")
        return matches
