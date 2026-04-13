from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    environment: str = "development"
    log_level: str = "INFO"
    secret_key: str = "CHANGE_ME_IN_PRODUCTION_USE_OPENSSL_RAND"

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/tablon"
    database_url_sync: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/tablon"

    # Redis (opcional)
    redis_url: str = ""

    # CORS
    frontend_url: str = "http://localhost:3000"

    # JWT
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7

    # Scraping
    scraping_enabled: bool = True
    scraping_timeout: int = 25

    # Deportes activos en el agregador /api/hoy
    active_sports: list[str] = [
        "futbol", "tenis", "basquet", "rugby",
        "hockey", "voley", "handball", "futsal",
        "boxeo", "golf", "motorsport", "motogp",
    ]

    # Cache TTLs (segundos)
    cache_ttl_live: int = 30
    cache_ttl_today: int = 300
    cache_ttl_results: int = 600
    cache_ttl_argentina: int = 60

    @property
    def allowed_origins(self) -> list[str]:
        return [o.strip() for o in self.frontend_url.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
