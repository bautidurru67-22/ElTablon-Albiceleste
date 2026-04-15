# ==========================================
# 🇦🇷 CLUBES ARGENTINOS (BASE REAL)
# ==========================================
CLUBES_ARGENTINOS = [
    "river", "boca", "racing", "independiente", "san lorenzo",
    "estudiantes", "gimnasia", "lanus", "banfield", "velez",
    "argentinos", "talleres", "belgrano", "newell", "central",
    "rosario central", "defensa", "huracan", "platense",
    "sarmiento", "arsenal", "colon", "union",
    "tigre", "barracas", "instituto"
]


def _is_club_argentino(team: str) -> bool:
    if not team:
        return False
    t = team.lower()
    return any(club in t for club in CLUBES_ARGENTINOS)


# ==========================================
# 🧠 CLASIFICACIÓN REAL (DEFINITIVA)
# ==========================================
def clasificar_partido(match: dict) -> str | None:
    home = match.get("home_team", "")
    away = match.get("away_team", "")
    comp = (match.get("competition") or "").lower()

    es_arg_home = _is_club_argentino(home)
    es_arg_away = _is_club_argentino(away)

    # ==========================================
    # 🇦🇷 SELECCIÓN
    # ==========================================
    if "argentina" in home.lower() or "argentina" in away.lower():
        return "selecciones"

    # ==========================================
    # 🇦🇷 LIGAS LOCALES
    # ==========================================
    if es_arg_home and es_arg_away:
        return "ligas_locales"

    # ==========================================
    # 🌍 EXTERIOR (SOLO SI HAY ARGENTINO)
    # ==========================================
    if es_arg_home or es_arg_away:
        # SOLO competencias internacionales válidas
        if any(x in comp for x in [
            "libertadores",
            "sudamericana",
            "champions",
            "europa",
            "mls",
            "copa",
            "league"
        ]):
            return "exterior"

    # ❌ DESCARTAR TODO LO DEMÁS
    return None
