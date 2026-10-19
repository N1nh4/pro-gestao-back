"""Ponto de entrada da API do SAC Pró-Gestão RPPS."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import api_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description=(
        "API do Sistema de Auditoria e Certificação Pró-Gestão RPPS — "
        "Manual MPS/PREVIC v4.1"
    ),
    version=settings.app_version,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/", include_in_schema=False)
def root():
    return {
        "status": "SAC Pró-Gestão API rodando",
        "versao": settings.app_version,
        "docs": "/api/docs",
    }
