"""Redis cache client for JARVISv4."""

from __future__ import annotations

import json
from typing import Any, Optional

import redis


class RedisCache:
    """Minimal Redis-backed cache for JSON-serializable payloads."""

    def __init__(self, redis_url: str, default_ttl_seconds: int = 300):
        self.redis_url = redis_url
        self.default_ttl_seconds = default_ttl_seconds
        self.client = redis.Redis.from_url(redis_url, decode_responses=True)

    def get_json(self, key: str) -> Optional[Any]:
        value = self.client.get(key)
        if value is None:
            return None
        if not isinstance(value, (str, bytes, bytearray)):
            return None
        return json.loads(value)

    def set_json(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        payload = json.dumps(value)
        self.client.setex(key, ttl, payload)