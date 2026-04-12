from fastapi import APIRouter
from scraping.registry import ADAPTER_REGISTRY

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok", "service": "tablon-albiceleste-api"}


@router.get("/debug/scrapers")
async def debug_scrapers():
    out = {}

    for sport, scraper_cls in ADAPTER_REGISTRY.items():
        try:
            scraper = scraper_cls()
            matches = await scraper.scrape()

            out[sport] = {
                "count": len(matches),
                "sample": [m.to_backend_dict() for m in matches[:3]],
            }

        except Exception as e:
            out[sport] = {
                "count": 0,
                "error": str(e),
            }

    return out
