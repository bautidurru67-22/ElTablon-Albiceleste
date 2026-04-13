@router.get("/debug/scraping")
async def debug_scraping(sport: str = "futbol"):
    """
    Corre scraping EN VIVO para un deporte y muestra resultado.
    Parámetro: ?sport=futbol|tenis|basquet|rugby|hockey|voley|handball|futsal|golf|boxeo|motorsport|motogp
    """
    t0 = time.monotonic()
    result: dict = {
        "sport": sport,
        "count": 0,
        "sample": [],
        "sources_tried": [],
        "errors": [],
        "duration_ms": 0,
    }

    try:
        from app.scraping_bridge import _SCRAPING_OK, _to_match
        result["scraping_ok"] = _SCRAPING_OK
        if not _SCRAPING_OK:
            result["errors"].append("scraping package not importable")
            return result

        from scraping.registry import ADAPTER_REGISTRY
        if sport not in ADAPTER_REGISTRY:
            result["errors"].append(f"'{sport}' no está en ADAPTER_REGISTRY. Disponibles: {list(ADAPTER_REGISTRY.keys())}")
            return result
        adapter_cls = ADAPTER_REGISTRY[sport]
        result["sources_tried"] = getattr(adapter_cls, "SOURCE_ORDER", [])
        result["source_diagnostics"] = getattr(adapter_cls, "LAST_RUN", {})

        from scraping.orchestrator.coordinator import ScrapingCoordinator
        coord = ScrapingCoordinator({sport: ADAPTER_REGISTRY[sport]}, timeout_per_adapter=25)
        normalized = await coord.run_all_flat()
        arg = coord.get_argentina_matches(normalized)

        result["count"] = len(arg)
        result["total_before_filter"] = len(normalized)
        result["sample"] = [
            {
                "home": m.home_team,
                "away": m.away_team,
                "score": f"{m.home_score}-{m.away_score}" if m.home_score is not None else None,
                "status": m.status,
                "minute": m.minute,
                "competition": m.competition,
                "source": m.source,
                "relevance": m.argentina_relevance,
                "start_time": m.start_time_arg,
            }
            for m in arg[:10]
        ]
    except Exception as e:
        logger.error(f"[debug/scraping] {sport}: {e}", exc_info=True)
        result["errors"].append(str(e))

    result["duration_ms"] = round((time.monotonic() - t0) * 1000)
    return result
