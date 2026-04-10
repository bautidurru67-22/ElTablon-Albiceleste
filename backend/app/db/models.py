"""
Modelos ORM — SQLAlchemy 2.0 style (Mapped / mapped_column).
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, Text,
    ForeignKey, UniqueConstraint, Index, Enum as SAEnum,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID]      = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str]         = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True)
    is_active: Mapped[bool]    = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    favorites: Mapped[list["Favorite"]] = relationship("Favorite", back_populates="user", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# Team
# ---------------------------------------------------------------------------
class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int]             = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str]           = mapped_column(String(100), unique=True, nullable=False, index=True)
    nombre: Mapped[str]         = mapped_column(String(200), nullable=False)
    deporte: Mapped[str]        = mapped_column(String(50), nullable=False, index=True)
    liga: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    pais: Mapped[str]           = mapped_column(String(100), default="Argentina")
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    players: Mapped[list["Player"]] = relationship("Player", back_populates="team")
    home_matches: Mapped[list["Match"]] = relationship("Match", foreign_keys="Match.equipo_local_id", back_populates="equipo_local")
    away_matches: Mapped[list["Match"]] = relationship("Match", foreign_keys="Match.equipo_visitante_id", back_populates="equipo_visitante")

    __table_args__ = (
        Index("ix_teams_deporte_liga", "deporte", "liga"),
    )


# ---------------------------------------------------------------------------
# Player
# ---------------------------------------------------------------------------
class Player(Base):
    __tablename__ = "players"

    id: Mapped[int]              = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str]            = mapped_column(String(100), unique=True, nullable=False, index=True)
    nombre: Mapped[str]          = mapped_column(String(200), nullable=False)
    deporte: Mapped[str]         = mapped_column(String(50), nullable=False, index=True)
    equipo_id: Mapped[Optional[int]] = mapped_column(ForeignKey("teams.id"), nullable=True, index=True)
    nacionalidad: Mapped[str]    = mapped_column(String(100), default="Argentina")
    posicion: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    ranking: Mapped[Optional[int]]  = mapped_column(Integer, nullable=True)
    stat_label: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    stat_value: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    foto_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    team: Mapped[Optional["Team"]] = relationship("Team", back_populates="players")

    __table_args__ = (
        Index("ix_players_deporte", "deporte"),
    )


# ---------------------------------------------------------------------------
# Match
# ---------------------------------------------------------------------------
class Match(Base):
    __tablename__ = "matches"

    id: Mapped[str]              = mapped_column(String(200), primary_key=True)
    deporte: Mapped[str]         = mapped_column(String(50), nullable=False, index=True)
    competition: Mapped[str]     = mapped_column(String(200), nullable=False)

    equipo_local_id: Mapped[Optional[int]]     = mapped_column(ForeignKey("teams.id"), nullable=True, index=True)
    equipo_visitante_id: Mapped[Optional[int]] = mapped_column(ForeignKey("teams.id"), nullable=True, index=True)
    equipo_local_nombre: Mapped[str]     = mapped_column(String(200), nullable=False)
    equipo_visitante_nombre: Mapped[str] = mapped_column(String(200), nullable=False)

    goles_local: Mapped[Optional[int]]     = mapped_column(Integer, nullable=True)
    goles_visitante: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    score_detail: Mapped[Optional[str]]    = mapped_column(String(100), nullable=True)

    estado: Mapped[str]              = mapped_column(String(20), nullable=False, index=True, default="upcoming")
    minuto: Mapped[Optional[str]]    = mapped_column(String(20), nullable=True)
    fecha: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    hora_arg: Mapped[Optional[str]]  = mapped_column(String(10), nullable=True)

    argentina_relevance: Mapped[str] = mapped_column(String(20), nullable=False, default="none", index=True)
    argentina_team: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    broadcast: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    source: Mapped[Optional[str]]    = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime]     = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime]     = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    equipo_local: Mapped[Optional["Team"]]     = relationship("Team", foreign_keys=[equipo_local_id],     back_populates="home_matches")
    equipo_visitante: Mapped[Optional["Team"]] = relationship("Team", foreign_keys=[equipo_visitante_id], back_populates="away_matches")
    live_events: Mapped[list["LiveEvent"]] = relationship("LiveEvent", back_populates="match", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_matches_deporte_estado", "deporte", "estado"),
        Index("ix_matches_fecha_estado",   "fecha",   "estado"),
        Index("ix_matches_argentina",      "argentina_relevance", "estado"),
    )


# ---------------------------------------------------------------------------
# LiveEvent
# ---------------------------------------------------------------------------
class LiveEvent(Base):
    __tablename__ = "live_events"

    id: Mapped[int]              = mapped_column(Integer, primary_key=True, autoincrement=True)
    partido_id: Mapped[str]      = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True)
    tipo_evento: Mapped[str]     = mapped_column(String(50), nullable=False)   # gol, tarjeta, cambio, etc.
    minuto: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    jugador: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    equipo: Mapped[Optional[str]]  = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime]   = mapped_column(DateTime(timezone=True), server_default=func.now())

    match: Mapped["Match"] = relationship("Match", back_populates="live_events")


# ---------------------------------------------------------------------------
# Favorite
# ---------------------------------------------------------------------------
class Favorite(Base):
    __tablename__ = "favorites"

    id: Mapped[int]          = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    tipo: Mapped[str]        = mapped_column(String(20), nullable=False)   # "equipo" | "jugador"
    entity_id: Mapped[str]   = mapped_column(String(100), nullable=False)  # slug del equipo o jugador
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="favorites")

    __table_args__ = (
        UniqueConstraint("user_id", "tipo", "entity_id", name="uq_favorite_user_entity"),
        Index("ix_favorites_user_tipo", "user_id", "tipo"),
    )
