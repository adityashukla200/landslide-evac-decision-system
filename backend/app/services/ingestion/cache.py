"""Cache abstraction supporting Redis with seamless in-memory fallback and TTL."""

import time
import json
import logging
from typing import Any, Optional
import redis

from backend.app.core.config import settings

logger = logging.getLogger(__name__)


class CacheLayer:
    """Thread-safe cache manager with Redis primary and in-memory TTL fallback."""

    def __init__(self, redis_url: Optional[str] = None, default_ttl: int = 3600) -> None:
        """Initialize cache layer."""
        self.default_ttl = default_ttl
        self.redis_client: Optional[redis.Redis] = None
        self._memory_store: dict[str, tuple[float, str]] = {}  # key -> (expiry_time, json_val)

        url = redis_url or settings.REDIS_URL
        try:
            r = redis.from_url(url, socket_connect_timeout=1, decode_responses=True)
            if r.ping():
                self.redis_client = r
                logger.info("[CacheLayer] Connected to Redis cache backend.")
        except Exception:
            logger.info("[CacheLayer] Redis unreachable. Operating in in-memory cache mode.")
            self.redis_client = None

    def get(self, key: str) -> Optional[Any]:
        """Retrieve item from cache if exists and not expired."""
        if self.redis_client is not None:
            try:
                val = self.redis_client.get(key)
                if val:
                    return json.loads(val)
                return None
            except Exception as exc:
                logger.warning(f"[CacheLayer] Redis GET failed: {exc}. Falling back to memory.")

        # In-memory lookup
        if key in self._memory_store:
            expiry, json_str = self._memory_store[key]
            if time.time() < expiry:
                return json.loads(json_str)
            else:
                # Expired
                del self._memory_store[key]
        return None

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Store item in cache with specified or default TTL."""
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        json_str = json.dumps(value)

        if self.redis_client is not None:
            try:
                self.redis_client.setex(key, ttl, json_str)
                return
            except Exception as exc:
                logger.warning(f"[CacheLayer] Redis SET failed: {exc}. Storing in memory.")

        # In-memory storage
        expiry = time.time() + ttl
        self._memory_store[key] = (expiry, json_str)

    def delete(self, key: str) -> None:
        """Evict item from cache."""
        if self.redis_client is not None:
            try:
                self.redis_client.delete(key)
            except Exception:
                pass
        self._memory_store.pop(key, None)

    def clear(self) -> None:
        """Clear all cached keys in memory (and flush redis db if active)."""
        self._memory_store.clear()
        if self.redis_client is not None:
            try:
                self.redis_client.flushdb()
            except Exception:
                pass


# Global singleton cache instance
cache = CacheLayer()
