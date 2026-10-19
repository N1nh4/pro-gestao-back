"""Configurações da aplicação (carregadas de variáveis de ambiente / .env)."""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── App ──────────────────────────────────────────────────────
    app_name: str = "SAC Pró-Gestão RPPS"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = True
    api_prefix: str = "/api"

    # ── Banco de dados ───────────────────────────────────────────
    database_url: str = (
        "postgresql+psycopg://sac_progestao:sac_progestao@localhost:5432/sac_progestao"
    )
    sql_echo: bool = False

    # ── Segurança / JWT ──────────────────────────────────────────
    secret_key: str = "troque-esta-chave-em-producao"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480

    # ── Redis (opcional por enquanto) ────────────────────────────
    redis_enabled: bool = False
    redis_url: str = "redis://localhost:6379/0"

    # ── CORS ─────────────────────────────────────────────────────
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_origins(cls, value: object) -> object:
        """Aceita lista ou string separada por vírgulas."""
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
