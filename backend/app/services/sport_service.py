from app.models.sport import SportSummary

SPORTS = [
    ("futbol",    "Fútbol"),
    ("tenis",     "Tenis"),
    ("basquet",   "Básquet"),
    ("hockey",    "Hockey"),
    ("rugby",     "Rugby"),
    ("voley",     "Voley"),
    ("boxeo",     "Boxeo"),
    ("futsal",    "Futsal"),
    ("polo",      "Polo"),
    ("golf",      "Golf"),
    ("handball",  "Handball"),
    ("esports",   "Esports"),
]


async def get_sports_summary() -> list[SportSummary]:
    result = []
    for slug, label in SPORTS:
        sport_matches = [m for m in MOCK_MATCHES if m.sport == slug]
        result.append(SportSummary(
            slug=slug,
            label=label,
            live_count=sum(1 for m in sport_matches if m.status == "live"),
            today_count=len(sport_matches),
        ))
    return result
