from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.db.session import get_db
from app.db.models import Favorite, User
from app.auth.dependencies import get_current_user
from app.schemas.auth import FavoriteCreate, FavoriteResponse

router = APIRouter()


@router.get("/", response_model=list[FavoriteResponse])
async def get_favorites(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Favorite).where(Favorite.user_id == current_user.id).order_by(Favorite.created_at.desc())
    )
    return result.scalars().all()


@router.post("/", response_model=FavoriteResponse, status_code=status.HTTP_201_CREATED)
async def add_favorite(
    body: FavoriteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.tipo not in ("equipo", "jugador"):
        raise HTTPException(status_code=400, detail="tipo debe ser 'equipo' o 'jugador'")

    # Idempotente — si ya existe, devuelve el existente
    existing = await db.execute(
        select(Favorite).where(
            Favorite.user_id == current_user.id,
            Favorite.tipo == body.tipo,
            Favorite.entity_id == body.entity_id,
        )
    )
    fav = existing.scalar_one_or_none()
    if fav:
        return fav

    fav = Favorite(user_id=current_user.id, tipo=body.tipo, entity_id=body.entity_id)
    db.add(fav)
    await db.commit()
    await db.refresh(fav)
    return fav


@router.delete("/{favorite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite(
    favorite_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Favorite).where(Favorite.id == favorite_id, Favorite.user_id == current_user.id)
    )
    fav = result.scalar_one_or_none()
    if not fav:
        raise HTTPException(status_code=404, detail="Favorito no encontrado")
    await db.delete(fav)
    await db.commit()


@router.delete("/by-entity/{tipo}/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite_by_entity(
    tipo: str,
    entity_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        delete(Favorite).where(
            Favorite.user_id == current_user.id,
            Favorite.tipo == tipo,
            Favorite.entity_id == entity_id,
        )
    )
    await db.commit()


@router.get("/check/{tipo}/{entity_id}")
async def check_favorite(
    tipo: str,
    entity_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(Favorite).where(
            Favorite.user_id == current_user.id,
            Favorite.tipo == tipo,
            Favorite.entity_id == entity_id,
        )
    )
    return {"is_favorite": result.scalar_one_or_none() is not None}
