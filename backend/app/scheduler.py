"""
Scheduler — jobs seguros y separados.
Si un job falla, la API sigue viva. Logs claros.
Jobs:
  job_futbol_live   → cada 30s
  job_futbol_hoy    → cada 30s
  resto de deportes → cada 90s
  job_hoy_agregador → cada 30s
"""
import logging
import time as _time
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.cache import cache
from app.config import settings

logger = logging.getLogger(__name__)
FAST_INTERVAL_FOOTBALL = 30
FAST_INTERVAL_AGGREGATOR = 30
DEFAULT_INTERVAL_OTHERS = 90


async def _run_sport(sport: str, status_filter: str | None = None) -> list:
    """Scrapea un deporte. Retorna lista de Match. Nunca lanza excepción."""
    try:
        from app.scraping_bridge import _SCRAPING_OK, _to_match
        if not _SCRAPING_OK:
            logger.warning(f"[_run_sport] scraping no disponible para {sport}")
            return []

        from scraping.registry import ADAPTER_REGISTRY
        from scraping.orchestrator.coordinator import ScrapingCoordinator

        if sport not in ADAPTER_REGISTRY:
            logger.warning(f"[_run_sport] {sport} no está en ADAPTER_REGISTRY")
            return []

        coordinator = ScrapingCoordinator(
            {sport: ADAPTER_REGISTRY[sport]},
            timeout_per_adapter=22,
        )
        normalized = await coordinator.run_all_flat()
        arg = coordinator.get_argentina_matches(normalized)

        # Cobertura rápida multi-deporte:
        # si un deporte no logra relevancia argentina, no devolver vacío total.
        # Esto ayuda a poblar /api/hoy mientras se afinan detectores por deporte.
        selected = arg if arg else ([] if sport == "futbol" else normalized)

        if status_filter:
            selected = [m for m in selected if m.status == status_filter]

        return [_to_match(m) for m in selected]

    except Exception as e:
        logger.error(f"[_run_sport] {sport} error: {e}", exc_info=True)
        return []


async def _cache_sport(key: str, sport: str,
                       ttl: int, status_filter: str | None = None) -> None:
    """Corre scraper y guarda en cache. Si falla, conserva último válido."""
    t0 = _time.monotonic()
    logger.info(f"[job] ▶ {key}")
    try:
        results = await _run_sport(sport, status_filter)
        if results:
            await cache.set(key, results, ttl=ttl, source=f"scraper/{sport}")
        elapsed = round((_time.monotonic() - t0) * 1000)
        logger.info(f"[job] ✓ {key} → {len(results)} partidos [{elapsed}ms]")
    except Exception as e:
        elapsed = round((_time.monotonic() - t0) * 1000)
        logger.error(f"[job] ✗ {key}: {e} [{elapsed}ms]")


# ── Jobs ───────────────────────────────────────────────────────────────────

async def job_futbol_live():
    await _cache_sport("live:futbol", "futbol",
                       ttl=settings.cache_ttl_live, status_filter="live")


async def job_futbol_hoy():
    await _cache_sport("today:futbol", "futbol", ttl=settings.cache_ttl_today)


async def job_tenis_hoy():
    await _cache_sport("today:tenis", "tenis", ttl=settings.cache_ttl_today)


async def job_basquet_hoy():
    await _cache_sport("today:basquet", "basquet", ttl=settings.cache_ttl_today)


async def job_rugby_hoy():
    await _cache_sport("today:rugby", "rugby", ttl=settings.cache_ttl_today)


async def job_hockey_hoy():
    await _cache_sport("today:hockey", "hockey", ttl=settings.cache_ttl_today)


def _make_sport_today_job(sport: str):
    async def _job():
        await _cache_sport(f"today:{sport}", sport, ttl=settings.cache_ttl_today)
    return _job


async def job_hoy_agregador():
    """
    Agrega todos los deportes en hoy:all.
    Lee caches individuales (no scrapea).
    Usa last_valid si el cache fresco expiró.
    """
    t0 = _time.monotonic()
    logger.info("[job] ▶ hoy:all")
    try:
        from app.models.match import Match

        all_matches: list[Match] = []

        for sport in settings.active_sports:
            key = f"today:{sport}"
            data = await cache.get(key)
            if data is None:
                data = await cache.get_last_valid(key)
            if data:
                all_matches.extend(data)

        STATUS_ORDER = {"live": 0, "upcoming": 1, "finished": 2}
        all_matches.sort(
            key=lambda m: (STATUS_ORDER.get(m.status, 9), m.start_time or "")
        )

        await cache.set("hoy:all", all_matches, ttl=60, source="agregador")

        elapsed = round((_time.monotonic() - t0) * 1000)
        live_n = sum(1 for m in all_matches if m.status == "live")
        by_sport: dict[str, int] = {}
        for m in all_matches:
            by_sport[m.sport] = by_sport.get(m.sport, 0) + 1
        sport_str = " ".join(f"{s}={n}" for s, n in by_sport.items())
        logger.info(
            f"[job] ✓ hoy:all → {len(all_matches)} total "
            f"({live_n} live) | {sport_str} [{elapsed}ms]"
        )
    except Exception as e:
        elapsed = round((_time.monotonic() - t0) * 1000)
        logger.error(f"[job] ✗ hoy:all: {e} [{elapsed}ms]")


# ── Build ──────────────────────────────────────────────────────────────────

def build_scheduler() -> AsyncIOScheduler:
    if not settings.scraping_enabled:
        logger.info("[scheduler] SCRAPING_ENABLED=false — scheduler vacío")
        return AsyncIOScheduler(timezone="America/Argentina/Buenos_Aires")

    sched = AsyncIOScheduler(timezone="America/Argentina/Buenos_Aires")

    sched.add_job(job_futbol_live,    IntervalTrigger(seconds=FAST_INTERVAL_FOOTBALL),
                  id="futbol_live",   max_instances=1, misfire_grace_time=10)
    sched.add_job(job_futbol_hoy,     IntervalTrigger(seconds=FAST_INTERVAL_FOOTBALL),
                  id="futbol_hoy",    max_instances=1, misfire_grace_time=30)
    sched.add_job(job_tenis_hoy,      IntervalTrigger(seconds=DEFAULT_INTERVAL_OTHERS),
                  id="tenis_hoy",     max_instances=1, misfire_grace_time=30)
    sched.add_job(job_basquet_hoy,    IntervalTrigger(seconds=DEFAULT_INTERVAL_OTHERS),
                  id="basquet_hoy",   max_instances=1, misfire_grace_time=30)
    sched.add_job(job_rugby_hoy,      IntervalTrigger(seconds=DEFAULT_INTERVAL_OTHERS),
                  id="rugby_hoy",     max_instances=1, misfire_grace_time=60)
    sched.add_job(job_hockey_hoy,     IntervalTrigger(seconds=DEFAULT_INTERVAL_OTHERS),
                  id="hockey_hoy",    max_instances=1, misfire_grace_time=60)
    sched.add_job(job_hoy_agregador,  IntervalTrigger(seconds=FAST_INTERVAL_AGGREGATOR),
                  id="hoy_agregador", max_instances=1, misfire_grace_time=30)

    # Alta rápida de más deportes activos (si existen en settings.active_sports)
    core_jobs = {"futbol", "tenis", "basquet", "rugby", "hockey"}
    for sport in settings.active_sports:
        if sport in core_jobs:
            continue
        sched.add_job(
            _make_sport_today_job(sport),
            IntervalTrigger(seconds=DEFAULT_INTERVAL_OTHERS),
            id=f"{sport}_hoy",
            max_instances=1,
            misfire_grace_time=60,
            replace_existing=True,
        )

    jobs = sched.get_jobs()
    logger.info(f"[scheduler] {len(jobs)} jobs: {[j.id for j in jobs]}")
    return sched
