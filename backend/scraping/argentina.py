def detect_argentina_relevance(
    home: str,
    away: str,
    competition: str = "",
    sport: str = "",
) -> tuple[ArgRelevance, str | None]:
    """
    Retorna (relevance, team_name).
    Orden: seleccion > club_arg > jugador_arg > competencia_arg > none
    """
    hn = normalize_str(home)
    an = normalize_str(away)
    cn = normalize_str(competition)

    def _contains(name_norm: str, hay_norm: str) -> bool:
        # Tokens cortos (ej: "arg") deben matchear palabra completa
        if len(name_norm) <= 3:
            return re.search(rf"\b{re.escape(name_norm)}\b", hay_norm) is not None
        return name_norm in hay_norm

    # 1. Selección nacional
    for name in _NATIONAL:
        nn = normalize_str(name)
        if nn and _contains(nn, hn):
            return "seleccion", home
        if nn and _contains(nn, an):
            return "seleccion", away

    # 2. Club argentino
    for club_n in _CLUBS:
        if club_n in hn:
            return "club_arg", home
        if club_n in an:
            return "club_arg", away

    # 3. Jugador argentino
    for player_n, pid in ARG_PLAYERS.items():
        pn = normalize_str(player_n)
        if pn in _NON_ARG:
            continue
        if pn and pn in hn:
            return "jugador_arg", home
        if pn and pn in an:
            return "jugador_arg", away

    # 4. Competencia argentina (club_arg en home por defecto)
    for ck in _ARG_COMPETITIONS:
        if ck in cn:
            return "club_arg", home

    return "none", None
