"""Routers da API agrupados num único roteador raiz."""

from fastapi import APIRouter

from app.api.routers import (
    admin,
    auth,
    bi,
    certificacoes,
    diagnostico,
    diligencias,
    health,
    operacional,
    plano,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(admin.router)
api_router.include_router(diagnostico.router)
api_router.include_router(plano.router)
api_router.include_router(diligencias.router)
api_router.include_router(bi.router)
api_router.include_router(certificacoes.router)
api_router.include_router(operacional.router)

__all__ = ["api_router"]
