from pydantic import BaseModel


class Player(BaseModel):
    id: str
    name: str
    sport: str
    team: str
    league: str
    country: str
    flag: str
    stat_value: str
    stat_label: str
    playing_today: bool = False
