from fastapi import APIRouter
from app.cache import cache
from app.scraping_bridge import ACTIVE_SPORTS
import time

router = APIRouter()


@router.get("/health")
async def health():
    """Health check básico."""
    return {"status": "ok", "service": "tablon-albiceleste-api"}


@router.get("/health/full")
async def health_full():
    """Health check completo: cache + scheduler + deportes activos."""
    cache_stats = await cache.stats()

    # Estado del scheduler
    from app.scheduler import scheduler
    scheduler_running = scheduler.running
    jobs = []
    if scheduler_running:
        for job in scheduler.get_jobs():
            next_run = job.next_run_time
            jobs.append({
                "id": job.id,
                "next_run": next_run.isoformat() if next_run else None,
            })

    # Cache keys activas por tipo
    keys = cache_stats.get("keys", [])
    cache_by_type = {
        "live":      [k for k in keys if k.startswith("live:")],
        "today":     [k for k in keys if k.startswith("today:")],
        "results":   [k for k in keys if k.startswith("results:")],
        "argentina": [k for k in keys if k.startswith("argentina:")],
    }

    return {
        "status": "ok",
        "timestamp": time.time(),
        "scheduler": {
            "running": scheduler_running,
            "jobs": jobs,
        },
        "cache": {
            "total_keys": cache_stats["total_keys"],
            "by_type": {k: len(v) for k, v in cache_by_type.items()},
        },
        "active_sports": ACTIVE_SPORTS,
    }
