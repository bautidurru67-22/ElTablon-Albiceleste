"""
Tenis argentino.

Fuentes:
1. ATP Tour JSON interno — scores en vivo y del día
2. TheSportsDB           — fixtures ATP/WTA
3. Sofascore             — fallback
"""
import logging
import re
from scraping.base_scraper import BaseScraper
from scraping.models import NormalizedMatch
from scraping.argentina import detect_argentina_relevance, normalize_str, ARG_PLAYERS
from scraping.sources.atp_live import get_live_scores
from scraping.sources.thesportsdb import get_events_today, parse_event
from scraping.sources.sofascore_safe import get_events_by_date as ss_today, get_live_events as ss_live
from scraping.normalizers import sofascore_normalizer

logger = logging.getLogger(__name__)

# IDs TheSportsDB para tenis
TSDB_TENNIS = {4926: "ATP Tour", 4927: "WTA Tour"}

ARG_LOWER = {normalize_str(k) for k in ARG_PLAYERS.keys()}


def _is_arg(name: str) -> bool:
    n = normalize_str(name)
    return any(a in n for a in ARG_LOWER)


def _make_tennis_match(home: str, away: str, comp: str,
                       status: str, raw: dict, source: str) -> NormalizedMatch | None:
    if not home or not away:
        return None
    if not _is_arg(home) and not _is_arg(away):
        return None
    relevance = "jugador_arg"
    arg_team = home if _is_arg(home) else away
    h_n = re.sub(r"\W+", "-", normalize_str(home))[:20]
    a_n = re.sub(r"\W+", "-", normalize_str(away))[:20]
    return NormalizedMatch(
        id=f"tenis-{source}-{h_n}-{a_n}",
        sport="tenis",
        source=source,
        competition=comp or "ATP Tour",
        home_team=home,
        away_team=away,
        home_score=raw.get("home_score"),
        away_score=raw.get("away_score"),
        score_detail=raw.get("score_detail", ""),
        status=status,
        minute=raw.get("minute"),
        start_time_arg=raw.get("start_time"),
        argentina_relevance=relevance,
        argentina_team=arg_team,
        raw=raw,
    )


class TennisAdapter(BaseScraper):

    async def scrape(self) -> list[NormalizedMatch]:
        matches: list[NormalizedMatch] = []
        seen: set[str] = set()

        def _add(m: NormalizedMatch | None) -> None:
            if m and m.id not in seen:
                seen.add(m.id)
                matches.append(m)

        # ── 1. ATP Tour JSON (primario) ───────────────────────────────────
        try:
            atp_matches = await get_live_scores()
            for raw in atp_matches:
                m = _make_tennis_match(
                    raw.get("home", ""), raw.get("away", ""),
                    raw.get("competition", ""), raw.get("status", "upcoming"),
                    raw, "atptour"
                )
                _add(m)
            logger.info(f"[tennis/atptour] {len(matches)}")
        except Exception as e:
            logger.warning(f"[tennis/atptour] {e}")

        # ── 2. TheSportsDB ────────────────────────────────────────────────
        try:
            before = len(matches)
            for lid, lname in TSDB_TENNIS.items():
                events = await get_events_today(lid)
                for ev in events:
                    raw = parse_event(ev, "tenis")
                    m = _make_tennis_match(
                        raw.get("home", ""), raw.get("away", ""),
                        raw.get("competition") or lname,
                        raw.get("status", "upcoming"), raw, "tsdb"
                    )
                    _add(m)
            logger.info(f"[tennis/thesportsdb] {len(matches) - before}")
        except Exception as e:
            logger.warning(f"[tennis/thesportsdb] {e}")

        # ── 3. Sofascore fallback ─────────────────────────────────────────
        if not matches:
            try:
                for fn in [ss_today, ss_live]:
                    data = await fn("tenis")
                    ss = sofascore_normalizer.normalize_events(data.get("events", []), "tenis")
                    for m in ss:
                        if m.id not in seen:
                            seen.add(m.id)
                            matches.append(m)
                logger.info(f"[tennis/sofascore-fallback] {len(matches)}")
            except Exception as e:
                logger.warning(f"[tennis/sofascore] {e}")

        logger.info(f"[tennis] TOTAL {len(matches)}")
        return matches
