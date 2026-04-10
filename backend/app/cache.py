"""
Cache unificado: Redis si REDIS_URL está configurado, MemoryCache como fallback.
Interface idéntica en ambos casos — el resto del código no sabe cuál usa.
"""
import time
import json
import asyncio
import logging
from dataclasses import dataclass
from typing import Any
from app.config import settings

logger = logging.getLogger(__name__)

TTL_MAP: dict[str, int] = {
    "live":       10,   # muy agresivo — partidos en vivo
    "today":      300,
    "results":    600,
    "argentina":  30,
    "sport":      120,
    "user":       60,
}
DEFAULT_TTL = 60


# ---------------------------------------------------------------------------
# Memory cache (fallback)
# ---------------------------------------------------------------------------
@dataclass
class _Entry:
    value: Any
    expires_at: float


class MemoryCache:
    def __init__(self):
        self._store: dict[str, _Entry] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        async with self._lock:
            e = self._store.get(key)
            if not e:
                return None
            if time.monotonic() > e.expires_at:
                del self._store[key]
                return None
            return e.value

    async def set(self, key: str, value: Any, ttl: int = DEFAULT_TTL) -> None:
        async with self._lock:
            self._store[key] = _Entry(value=value, expires_at=time.monotonic() + ttl)

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._store.pop(key, None)

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()

    async def stats(self) -> dict:
        async with self._lock:
            now = time.monotonic()
            active = [k for k, v in self._store.items() if v.expires_at > now]
            return {"backend": "memory", "total_keys": len(active), "keys": active}

    def ttl_for(self, cache_type: str) -> int:
        return TTL_MAP.get(cache_type, DEFAULT_TTL)


# ---------------------------------------------------------------------------
# Redis cache
# ---------------------------------------------------------------------------
class RedisCache:
    def __init__(self, redis_url: str):
        import redis.asyncio as aioredis
        self._client = aioredis.from_url(redis_url, decode_responses=True)

    async def get(self, key: str) -> Any | None:
        try:
            raw = await self._client.get(key)
            return json.loads(raw) if raw else None
        except Exception as e:
            logger.warning(f"[redis] get failed: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int = DEFAULT_TTL) -> None:
        try:
            await self._client.set(key, json.dumps(value, default=str), ex=ttl)
        except Exception as e:
            logger.warning(f"[redis] set failed: {e}")

    async def delete(self, key: str) -> None:
        try:
            await self._client.delete(key)
        except Exception as e:
            logger.warning(f"[redis] delete failed: {e}")

    async def clear(self) -> None:
        try:
            await self._client.flushdb()
        except Exception as e:
            logger.warning(f"[redis] clear failed: {e}")

    async def stats(self) -> dict:
        try:
            info = await self._client.info("keyspace")
            return {"backend": "redis", "info": str(info)}
        except Exception:
            return {"backend": "redis", "info": "unavailable"}

    def ttl_for(self, cache_type: str) -> int:
        return TTL_MAP.get(cache_type, DEFAULT_TTL)


# ---------------------------------------------------------------------------
# Factory — singleton
# ---------------------------------------------------------------------------
def _build_cache():
    if settings.redis_url:
        try:
            c = RedisCache(settings.redis_url)
            logger.info(f"Cache: Redis ({settings.redis_url[:20]}...)")
            return c
        except Exception as e:
            logger.warning(f"Redis no disponible ({e}), usando MemoryCache")
    logger.info("Cache: MemoryCache (in-process)")
    return MemoryCache()


cache = _build_cache()
