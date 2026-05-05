import json

from redis.asyncio import Redis

from app.core.config import get_settings


_redis: Redis | None = None


def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(get_settings().redis_url, decode_responses=True)
    return _redis


async def ping_redis() -> bool:
    try:
        return bool(await get_redis().ping())
    except Exception:  # noqa: BLE001
        return False


async def get_json(key: str) -> dict | list | None:
    try:
        payload = await get_redis().get(key)
    except Exception:  # noqa: BLE001
        return None
    if not payload:
        return None
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return None


async def set_json(key: str, value: dict | list, ttl_seconds: int) -> bool:
    try:
        await get_redis().set(key, json.dumps(value), ex=ttl_seconds)
        return True
    except Exception:  # noqa: BLE001
        return False


async def delete_key(key: str) -> bool:
    try:
        await get_redis().delete(key)
        return True
    except Exception:  # noqa: BLE001
        return False
