from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.editorial_sources import SOURCE_MATRIX, get_sport_matrix, list_sports

router = APIRouter()


@router.get("/matrix")
async def get_sources_matrix(include_pending: bool = Query(default=True)):
    """Devuelve la matriz de fuentes completa.

    - include_pending=true: incluye deportes marcados como pending_validation.
    - include_pending=false: filtra entradas pendientes.
    """
    if include_pending:
        return SOURCE_MATRIX

    sports = SOURCE_MATRIX.get("sports", {})
    filtered = {
        sport: value
        for sport, value in sports.items()
        if not (isinstance(value, dict) and value.get("status") == "pending_validation")
    }
    return {
        **SOURCE_MATRIX,
        "sports": filtered,
    }


@router.get("/matrix/sports")
async def get_sources_sports():
    return {"sports": list_sports()}


@router.get("/matrix/{sport}")
async def get_sources_matrix_by_sport(sport: str):
    data = get_sport_matrix(sport)
    if not data:
        raise HTTPException(status_code=404, detail=f"Sport '{sport}' no encontrado en matriz")
    return {"sport": sport, "matrix": data}
