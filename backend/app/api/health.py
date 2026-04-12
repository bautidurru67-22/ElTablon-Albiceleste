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


@router.get("/debug/scraping")
async def debug_scraping():
    """Ejecuta scraping en tiempo real y retorna resultado crudo con logs. SOLO PARA DEBUG."""
    import time
    start = time.monotonic()
    result = {"adapters": {}, "total": 0, "errors": [], "duration_ms": 0}

    try:
        from app.scraping_bridge import _SCRAPING_OK, ACTIVE_SPORTS
        result["scraping_importable"] = _SCRAPING_OK
        result["active_sports"] = ACTIVE_SPORTS

        if not _SCRAPING_OK:
            result["errors"].append("scraping package not importable")
            return result

        from scraping.registry import ADAPTER_REGISTRY
        result["registry_sports"] = list(ADAPTER_REGISTRY.keys())

        # Run ONE sport (football) as test
        from scraping.orchestrator.coordinator import ScrapingCoordinator
        test_adapter = {k: v for k, v in ADAPTER_REGISTRY.items() if k in ["futbol"]}
        coordinator = ScrapingCoordinator(test_adapter, timeout_per_adapter=20)
        all_matches = await coordinator.run_all_flat()
        arg = coordinator.get_argentina_matches(all_matches)

        result["adapters"]["futbol"] = {
            "total_scraped": len(all_matches),
            "argentina_filtered": len(arg),
            "sample": [
                {"home": m.home_team, "away": m.away_team,
                 "score": f"{m.home_score}-{m.away_score}" if m.home_score is not None else None,
                 "status": m.status, "source": m.source}
                for m in arg[:5]
            ]
        }
        result["total"] = len(arg)

    except Exception as e:
        result["errors"].append(str(e))

    result["duration_ms"] = round((time.monotonic() - start) * 1000)
    return result
