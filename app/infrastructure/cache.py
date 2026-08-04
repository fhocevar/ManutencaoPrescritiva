import json
from typing import Any

import redis.asyncio as redis


class RedisCache:
    def __init__(self, url: str, ttl_seconds: int) -> None:
        self.client = redis.from_url(url, decode_responses=True)
        self.ttl_seconds = ttl_seconds

    async def get_json(self, key: str) -> Any | None:
        value = await self.client.get(key)
        return json.loads(value) if value else None

    async def set_json(self, key: str, value: Any) -> None:
        await self.client.setex(key, self.ttl_seconds, json.dumps(value, default=str))
