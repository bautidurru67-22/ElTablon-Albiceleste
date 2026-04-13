"""
Vóley argentino.

Fuentes:
1. TheSportsDB — FIVB, Liga Argentina
2. Sofascore   — fallback
"""
import logging
import re
from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch
from scraping.argentina import detect_argentina_relevance, normalize_str
from scraping.sources.thesportsdb import get_events_today, parse_event
from scraping.sources.sofascore_safe import get_events_by_date as ss_today, get_live_events as ss_live
from scraping.normalizers import sofascore_normalizer

logger = logging.getLogger(__name__)

TSDB_VOLEY = {5028: "FIVB Volleyball"}


def _make_match(raw: dict, source: str) -> NormalizedMatch | None:
    home = raw.get("home", "").strip()
    away = raw.get("away", "").strip()
    if not home or not away:
        return None
    comp = raw.get("competition", "") or ""
    relevance, arg_team = detect_argentina_relevance(home, away, comp, "voley")
    if relevance == "none":
        return None
    h_n = re.sub(r"\W+", "-", normalize_str(home))[:20]
    a_n = re.sub(r"\W+", "-", normalize_str(away))[:20]
    return NormalizedMatch(
        id=f"voley-{source}-{h_n}-{a_n}",
        sport="voley", source=source, competition=comp or "Vóley",
        home_team=home, away_team=away,
        home_score=raw.get("home_score"), away_score=raw.get("away_score"),
        status=raw.get("status", "upcoming"), start_time_arg=raw.get("start_time"),
        argentina_relevance=relevance, argentina_team=arg_team, raw=raw,
    )


class VolleyballAdapter(BaseScraper):

    async def scrape(self) -> list[NormalizedMatch]:
        matches: list[NormalizedMatch] = []
        seen: set[str] = set()

        def _add(m):
            if m and m.id not in seen:
                seen.add(m.id)
                matches.append(m)

        try:
            for lid, lname in TSDB_VOLEY.items():
                for ev in await get_events_today(lid):
                    raw = parse_event(ev, "voley")
                    raw["competition"] = raw.get("competition") or lname
                    _add(_make_match(raw, "tsdb"))
            logger.info(f"[volleyball/tsdb] {len(matches)}")
        except Exception as e:
            logger.warning(f"[volleyball/tsdb] {e}")

        if not matches:
            try:
                for fn in [ss_today, ss_live]:
                    data = await fn("voley")
                    for m in sofascore_normalizer.normalize_events(data.get("events", []), "voley"):
                        if m.id not in seen:
                            seen.add(m.id); matches.append(m)
                logger.info(f"[volleyball/sofascore] {len(matches)}")
            except Exception as e:
                logger.warning(f"[volleyball/sofascore] {e}")

        logger.info(f"[volleyball] TOTAL {len(matches)}")
        return matches
