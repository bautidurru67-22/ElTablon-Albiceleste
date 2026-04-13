"""
Cache central — MemoryCache (default) o Redis si REDIS_URL configurado.
Guarda: data + timestamp + source + status.
Conserva último valor válido aunque expire (get_last_valid).
"""
import time
import json
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any
from app.config import settings

logger = logging.getLogger(__name__)

DEFAULT_TTL = 60

TTL_MAP: dict[str, int] = {
    "live":       30,
    "today":      300,
    "results":    600,
    "argentina":  60,
    "futbol":     120,
    "tenis":      300,
    "basquet":    300,
    "hoy":        60,
}


@dataclass
class _Entry:
    value: Any
    expires_at: float
    timestamp: float = field(default_factory=time.time)
    source: str = "cache"
    status: str = "ok"


class MemoryCache:
    def __init__(self):
        self._store: dict[str, _Entry] = {}
        self._last_valid: dict[str, _Entry] = {}   # nunca expira, último dato bueno
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

    async def set(self, key: str, value: Any,
                  ttl: int = DEFAULT_TTL,
                  source: str = "scraper") -> None:
        async with self._lock:
            entry = _Entry(
                value=value,
                expires_at=time.monotonic() + ttl,
                timestamp=time.time(),
                source=source,
                status="ok",
            )
            self._store[key] = entry
            if value:  # solo guarda último válido si tiene datos
                self._last_valid[key] = entry

    async def get_last_valid(self, key: str) -> Any | None:
        """Retorna el último dato válido aunque haya expirado. Nunca None si hubo datos."""
        async with self._lock:
            e = self._last_valid.get(key)
            return e.value if e else None

    async def get_meta(self, key: str) -> dict:
        """Retorna metadata del entry: timestamp, source, status, age_s."""
        async with self._lock:
            e = self._store.get(key) or self._last_valid.get(key)
            if not e:
                return {"exists": False}
            return {
                "exists": True,
                "timestamp": e.timestamp,
                "source": e.source,
                "status": e.status,
                "age_s": round(time.time() - e.timestamp),
                "expired": time.monotonic() > e.expires_at,
            }

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
            return {
                "backend": "memory",
                "total_keys": len(active),
                "keys": active,
                "last_valid_keys": list(self._last_valid.keys()),
            }

    def ttl_for(self, cache_type: str) -> int:
        return TTL_MAP.get(cache_type, DEFAULT_TTL)


class RedisCache:
    def __init__(self, redis_url: str):
        import redis.asyncio as aioredis
        self._client = aioredis.from_url(redis_url, decode_responses=True)

    async def get(self, key: str) -> Any | None:
        try:
            raw = await self._client.get(key)
            return json.loads(raw) if raw else None
        except Exception as e:
            logger.warning(f"[redis.get] {key}: {e}")
            return None

    async def set(self, key: str, value: Any,
                  ttl: int = DEFAULT_TTL,
                  source: str = "scraper") -> None:
        try:
            payload = json.dumps({"data": value, "source": source, "ts": time.time()},
                                 default=str)
            await self._client.set(key, payload, ex=ttl)
            if value:
                await self._client.set(f"lv:{key}", payload)  # last_valid sin TTL
        except Exception as e:
            logger.warning(f"[redis.set] {key}: {e}")

    async def get_last_valid(self, key: str) -> Any | None:
        try:
            raw = await self._client.get(f"lv:{key}")
            if not raw:
                return None
            return json.loads(raw).get("data")
        except Exception as e:
            logger.warning(f"[redis.get_last_valid] {key}: {e}")
            return None

    async def get_meta(self, key: str) -> dict:
        try:
            raw = await self._client.get(key)
            if not raw:
                return {"exists": False}
            d = json.loads(raw)
            return {"exists": True, "source": d.get("source"), "timestamp": d.get("ts")}
        except Exception:
            return {"exists": False}

    async def delete(self, key: str) -> None:
        try:
            await self._client.delete(key)
        except Exception:
            pass

    async def clear(self) -> None:
        try:
            await self._client.flushdb()
        except Exception:
            pass

    async def stats(self) -> dict:
        try:
            info = await self._client.info("keyspace")
            return {"backend": "redis", "info": str(info)}
        except Exception:
            return {"backend": "redis", "info": "unavailable"}

    def ttl_for(self, cache_type: str) -> int:
        return TTL_MAP.get(cache_type, DEFAULT_TTL)


def _build_cache():
    if settings.redis_url:
        try:
            c = RedisCache(settings.redis_url)
            logger.info(f"[cache] Redis ({settings.redis_url[:30]}...)")
            return c
        except Exception as e:
            logger.warning(f"[cache] Redis falló ({e}), usando MemoryCache")
    logger.info("[cache] MemoryCache")
    return MemoryCache()


cache = _build_cache()
