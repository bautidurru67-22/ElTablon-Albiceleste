from app.models.player import Player

MOCK_ABROAD: list[Player] = [
    Player(id="campazzo", name="Facundo Campazzo", sport="basquet",
           team="Dallas Mavericks", league="NBA", country="Estados Unidos",
           flag="🇺🇸", stat_value="14.2", stat_label="pts", playing_today=False),
    Player(id="bolmaro", name="Leandro Bolmaro", sport="basquet",
           team="FC Barcelona", league="ACB", country="España",
           flag="🇪🇸", stat_value="11.8", stat_label="pts", playing_today=False),
    Player(id="cerundolo", name="Francisco Cerúndolo", sport="tenis",
           team="ATP Tour", league="Masters 1000 Madrid", country="España",
           flag="🇪🇸", stat_value="#10", stat_label="ranking", playing_today=True),
    Player(id="etcheverry", name="Tomás Etcheverry", sport="tenis",
           team="ATP Tour", league="Masters 1000 Madrid", country="España",
           flag="🇪🇸", stat_value="#30", stat_label="ranking", playing_today=True),
    Player(id="icardi", name="Mauro Icardi", sport="futbol",
           team="Galatasaray", league="Süper Lig", country="Turquía",
           flag="🇹🇷", stat_value="18", stat_label="goles", playing_today=False),
    Player(id="laprovittola", name="Nicolás Laprovíttola", sport="basquet",
           team="Laga Basket", league="ACB", country="España",
           flag="🇪🇸", stat_value="9.4", stat_label="pts", playing_today=False),
]


async def get_argentines_abroad() -> list[Player]:
    return MOCK_ABROAD
