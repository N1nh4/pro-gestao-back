"""Segurança: hash de senha (bcrypt) e JWT (python-jose)."""

from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()

# bcrypt opera sobre os primeiros 72 bytes da senha.
_BCRYPT_MAX_BYTES = 72


def hash_senha(senha: str) -> str:
    """Gera o hash bcrypt de uma senha em texto puro."""
    senha_bytes = senha.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(senha_bytes, bcrypt.gensalt()).decode("utf-8")


def verificar_senha(senha: str, senha_hash: str) -> bool:
    """Confere a senha contra o hash armazenado."""
    try:
        senha_bytes = senha.encode("utf-8")[:_BCRYPT_MAX_BYTES]
        return bcrypt.checkpw(senha_bytes, senha_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def criar_token(data: dict[str, Any], expires_minutes: int | None = None) -> str:
    """Cria um JWT assinado com expiração."""
    payload = data.copy()
    expire = datetime.now(UTC) + timedelta(
        minutes=expires_minutes or settings.access_token_expire_minutes
    )
    payload.update({"exp": expire, "iat": datetime.now(UTC)})
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decodificar_token(token: str) -> dict[str, Any]:
    """Decodifica e valida um JWT. Levanta JWTError se inválido/expirado."""
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])


__all__ = [
    "JWTError",
    "criar_token",
    "decodificar_token",
    "hash_senha",
    "verificar_senha",
]
