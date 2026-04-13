from fastapi import APIRouter
from scraping.adapters.football import FootballAdapter

router = APIRouter()

@router.get("/debug/scraping")
async def debug_scraping():
    adapter = FootballAdapter()
    matches = await adapter.scrape()

    return {
        "count": len(matches),
        "sample": [m.__dict__ for m in matches[:5]]
    }
