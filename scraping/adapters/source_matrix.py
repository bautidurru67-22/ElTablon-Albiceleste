"""Prioridad de fuentes por deporte alineada a la matriz editorial.

Este módulo traduce la matriz de URLs a nombres de proveedores usados por adapters.
"""

from __future__ import annotations

SOURCE_ORDER_BY_SPORT: dict[str, list[str]] = {
    "futbol": ["afa", "lpf", "espn", "promiedos", "api_football", "sofascore", "flashscore"],
    "tenis": ["aat", "itf", "atptour", "wtatennis", "espn", "sofascore", "flashscore"],
    "basquet": ["argentina_basketball", "fiba", "lnb", "espn", "sofascore", "flashscore"],
    "rugby": ["urba", "world_rugby", "espn", "aplenorugby", "sofascore", "flashscore"],
    "hockey": ["cah", "fih", "espn", "sofascore"],
    "voley": ["feva", "volleyballworld", "aclav", "espn", "flashscore", "sofascore"],
    "handball": ["cah_handball", "ihf", "sofascore"],
    "futsal": ["afa", "parenlapelota", "pasionfutsal", "sofascore"],
    "motorsport": ["formula1", "fia", "actc", "openf1", "espn", "sofascore"],
    "motogp": ["motogp", "espn", "sofascore"],
    "boxeo": ["fab", "boxrec", "tapology", "sofascore"],
    "golf": ["aag", "randa", "usga", "wagr", "espn", "sofascore"],
    "polo": ["aapolo", "sofascore"],
    "esports": ["deva", "afa_esports", "liquipedia", "vlr", "sofascore"],
    "dakar": ["fia", "espn", "sofascore"],
    "olimpicos": ["coarg", "olympics", "sofascore"],
}


def get_adapter_source_order(sport: str, fallback: list[str] | None = None) -> list[str]:
    order = SOURCE_ORDER_BY_SPORT.get(sport)
    if order:
        return order
    return fallback or ["sofascore"]
