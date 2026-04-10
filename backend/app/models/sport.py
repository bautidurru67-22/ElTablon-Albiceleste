from pydantic import BaseModel


class SportSummary(BaseModel):
    slug: str
    label: str
    live_count: int = 0
    today_count: int = 0
