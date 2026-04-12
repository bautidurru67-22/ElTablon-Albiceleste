"""
NormalizedMatch — contrato de datos entre scrapers y backend.
Todos los adapters deben producir este formato.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

ArgRelevance = Literal["seleccion", "club_arg", "jugador_arg", "none"]
MatchStatus  = Literal["live", "upcoming", "finished"]


@dataclass
class NormalizedMatch:
    # Identidad
    id: str                          # "{sport}-{source}-{home_slug}-{away_slug}"
    sport: str                       # "futbol", "tenis", "basquet" …
    source: str                      # "sofascore", "atptour", "promiedos" …

    # Competencia
    competition: str                 # "Liga Profesional Argentina"
    competition_id: str | None = None

    # Equipos / jugadores
    home_team: str  = ""
    away_team: str  = ""
    home_team_id: str | None = None
    away_team_id: str | None = None

    # Marcador
    home_score: int | None = None
    away_score: int | None = None
    score_detail: str | None = None  # "6-4 7-5" (tenis), "54-61 3T" (básquet)

    # Estado
    status: MatchStatus = "upcoming"
    minute: str | None = None        # "69'" / "3er C" / "En cancha"

    # Tiempo
    datetime_utc: datetime | None = None
    start_time_arg: str | None = None  # "21:30" hora local Argentina

    # Relevancia argentina
    argentina_relevance: ArgRelevance = "none"
    argentina_team: str | None = None  # nombre del equipo/jugador ARG

    # Broadcast
    broadcast: str | None = None

    # Metadata interna
    raw: dict = field(default_factory=dict, repr=False)  # payload original


    def to_backend_dict(self) -> dict:
        """Convierte al formato esperado por el backend FastAPI."""
        return {
            "id": self.id,
            "sport": self.sport,
            "competition": self.competition,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "home_score": self.home_score,
            "away_score": self.away_score,
            "status": self.status,
            "minute": self.minute,
            "datetime": self.datetime_utc.isoformat() if self.datetime_utc else None,
            "start_time": self.start_time_arg,
            "argentina_relevance": self.argentina_relevance,
            "argentina_team": self.argentina_team,
            "broadcast": self.broadcast,
        }
