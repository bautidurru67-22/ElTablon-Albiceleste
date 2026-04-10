"""
Scheduler de scraping — background jobs separados de la API.
Jobs:
  _job_live    → cada 45s  (configurable via SCHEDULER_LIVE_INTERVAL)
  _job_today   → cada 5min
  _job_results → cada 10min
"""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.cache import cache
from app.config import settings
from app.scraping_bridge import (
    ACTIVE_SPORTS,
    fetch_live_from_scrapers,
    fetch_today_from_scrapers,
    fetch_results_from_scrapers,
)

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="America/Argentina/Buenos_Aires")


async def _job_live():
    if not settings.scraping_enabled:
        return
    try:
        matches = await fetch_live_from_scrapers()
        ttl = settings.cache_ttl_live
        await cache.set("live:all", matches, ttl=ttl)
        for sport in ACTIVE_SPORTS:
            await cache.set(f"live:{sport}", [m for m in matches if m.sport == sport], ttl=ttl)
        logger.info(f"[scheduler/live] {len(matches)} en vivo")
    except Exception as e:
        logger.error(f"[scheduler/live] {e}")


async def _job_today():
    if not settings.scraping_enabled:
        return
    try:
        matches = await fetch_today_from_scrapers()
        ttl = settings.cache_ttl_today
        await cache.set("today:all", matches, ttl=ttl)
        for sport in ACTIVE_SPORTS:
            await cache.set(f"today:{sport}", [m for m in matches if m.sport == sport], ttl=ttl)
        arg = [m for m in matches if m.argentina_relevance != "none"]
        await cache.set("argentina:all", arg, ttl=settings.cache_ttl_argentina)
        logger.info(f"[scheduler/today] {len(matches)} totales · {len(arg)} ARG")
    except Exception as e:
        logger.error(f"[scheduler/today] {e}")


async def _job_results():
    if not settings.scraping_enabled:
        return
    try:
        matches = await fetch_results_from_scrapers()
        ttl = settings.cache_ttl_results
        await cache.set("results:all", matches, ttl=ttl)
        for sport in ACTIVE_SPORTS:
            await cache.set(f"results:{sport}", [m for m in matches if m.sport == sport], ttl=ttl)
        logger.info(f"[scheduler/results] {len(matches)} finalizados")
    except Exception as e:
        logger.error(f"[scheduler/results] {e}")


def setup_scheduler() -> AsyncIOScheduler:
    scheduler.add_job(
        _job_live, IntervalTrigger(seconds=settings.scheduler_live_interval),
        id="job_live", replace_existing=True, max_instances=1, misfire_grace_time=10,
    )
    scheduler.add_job(
        _job_today, IntervalTrigger(seconds=settings.scheduler_today_interval),
        id="job_today", replace_existing=True, max_instances=1, misfire_grace_time=30,
    )
    scheduler.add_job(
        _job_results, IntervalTrigger(seconds=settings.scheduler_results_interval),
        id="job_results", replace_existing=True, max_instances=1, misfire_grace_time=60,
    )
    return scheduler
