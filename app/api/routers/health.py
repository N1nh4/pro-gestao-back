"""Health check do sistema."""

from fastapi import APIRouter

from app.core.config import get_settings
from app.core.redis import redis_health

router = APIRouter(tags=["Sistema"])


@router.get("/api/health")
def health():
    settings = get_settings()
    return {
        "status": "online",
        "sistema": settings.app_name,
        "versao": settings.app_version,
        "ambiente": settings.environment,
        "redis": redis_health(),
    }
