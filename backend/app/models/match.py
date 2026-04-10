from pydantic import BaseModel
from datetime import datetime
from typing import Literal, Optional


class Match(BaseModel):
    id: str
    sport: str  # "futbol", "tenis", "basquet", etc.
    competition: str  # "Liga Profesional Argentina"
    home_team: str
    away_team: str

    home_score: Optional[int] = None
    away_score: Optional[int] = None

    status: Literal["live", "upcoming", "finished"]
    minute: Optional[str] = None  # "69'" / "3er C" / "2do set"

    datetime: Optional[datetime] = None  # fecha y hora UTC del partido
    start_time: Optional[str] = None  # "21:30" - hora local ARG (display)

    argentina_relevance: Literal["seleccion", "club_arg", "jugador_arg", "none"] = "none"
    argentina_team: Optional[str] = None  # equipo/jugador ARG involucrado

    broadcast: Optional[str] = None  # "TyC Sports", "ESPN 3", etc.
