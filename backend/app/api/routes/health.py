from fastapi import APIRouter

from app.core.config import get_settings
from app.db.redis_client import ping_redis


router = APIRouter(tags=["health"])


@router.get("/health")
async def healthcheck():
    settings = get_settings()
    redis_connected = await ping_redis()
    return {
        "status": "ok",
        "app": settings.app_name,
        "demo_mode": settings.demo_mode,
        "redis": {
            "connected": redis_connected,
            "preview_cache_enabled": redis_connected,
            "preview_cache_ttl_seconds": settings.preview_cache_ttl_seconds,
            "dashboard_cache_ttl_seconds": settings.dashboard_cache_ttl_seconds,
        },
        "ports": {"frontend": 3000, "backend": 8000},
    }
