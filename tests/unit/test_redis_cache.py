from typing import Optional

from backend.core.cache.redis_cache import RedisCache


class FakeRedisClient:
    def __init__(self) -> None:
        self.storage: dict[str, str] = {}
        self.last_setex: Optional[tuple[str, int, str]] = None
        self.get_calls = 0

    def get(self, key: str) -> Optional[str]:
        self.get_calls += 1
        return self.storage.get(key)

    def setex(self, key: str, ttl_seconds: int, value: str) -> None:
        self.last_setex = (key, ttl_seconds, value)
        self.storage[key] = value


def test_redis_cache_roundtrip_json() -> None:
    fake_client = FakeRedisClient()
    cache = RedisCache("redis://example:6379/0", client=fake_client)

    payload = {"title": "Cached Result", "url": "http://cached"}
    cache.set_json("web_search:duckduckgo:5:test", payload, ttl_seconds=120)

    assert fake_client.last_setex is not None
    key, ttl, stored_value = fake_client.last_setex
    assert key == "web_search:duckduckgo:5:test"
    assert ttl == 120
    assert stored_value == '{"title": "Cached Result", "url": "http://cached"}'

    loaded = cache.get_json("web_search:duckduckgo:5:test")
    assert loaded == payload
    assert fake_client.get_calls == 1