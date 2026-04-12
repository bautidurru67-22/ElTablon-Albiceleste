from fastapi import APIRouter, Query
from app.scraping_bridge import (
    fetch_live_from_scrapers,
    fetch_today_from_scrapers,
    fetch_results_from_scrapers,
)

router = APIRouter()


@router.get("/live")
async def get_live(sport: str | None = Query(None)):
    data = await fetch_live_from_scrapers()

    if sport:
        data = [m for m in data if m.sport == sport]

    return data


@router.get("/today")
async def get_today(sport: str | None = Query(None)):
    data = await fetch_today_from_scrapers()

    if sport:
        data = [m for m in data if m.sport == sport]

    return data


@router.get("/results")
async def get_results(sport: str | None = Query(None)):
    data = await fetch_results_from_scrapers()

    if sport:
        data = [m for m in data if m.sport == sport]

    return data
