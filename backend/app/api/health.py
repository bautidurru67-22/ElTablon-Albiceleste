from fastapi import APIRouter
from scraping.adapters.football import FootballAdapter

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok", "service": "tablon-albiceleste-api"}


@router.get("/debug/scraping")
async def debug_scraping():
    adapter = FootballAdapter()
    matches = await adapter.scrape()

    return {
        "count": len(matches),
        "sample": [m.to_backend_dict() for m in matches[:5]],
    }
