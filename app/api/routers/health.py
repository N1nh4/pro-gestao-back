"""Health check do sistema."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.core.redis import redis_health
from app.db.base import SessionLocal

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


@router.get("/api/health/ready")
def ready():
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Banco de dados indisponível",
        ) from exc

    return {"status": "ready"}
