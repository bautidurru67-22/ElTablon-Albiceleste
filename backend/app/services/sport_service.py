from app.services.match_service import get_today_matches, get_live_matches

def get_sports_summary():
    today_matches = get_today_matches()
    live_matches = get_live_matches()

    return {
        "sports": [],
        "today_count": len(today_matches) if isinstance(today_matches, list) else 0,
        "live_count": len(live_matches) if isinstance(live_matches, list) else 0,
    }
