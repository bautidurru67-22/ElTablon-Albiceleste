from pydantic import BaseModel
from datetime import datetime
from typing import Literal


class Match(BaseModel):
    id: str
    sport: str                          # "futbol", "tenis", "basquet", etc.
    competition: str                    # "Liga Profesional Argentina"
    home_team: str
    away_team: str
    home_score: int | None = None
    away_score: int | None = None
    status: Literal["live", "upcoming", "finished"]
    minute: str | None = None           # "69'" / "3er C" / "2do set"
    datetime: datetime | None = None    # fecha y hora UTC del partido
    start_time: str | None = None       # "21:30" — hora local ARG (display)
    argentina_relevance: Literal["seleccion", "club_arg", "jugador_arg", "none"] = "none"
    argentina_team: str | None = None   # equipo/jugador ARG involucrado
    broadcast: str | None = None        # "TyC Sports", "ESPN 3", etc.
