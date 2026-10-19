"""Cliente Redis (opcional).

Ainda não há features que dependam do Redis; este módulo apenas centraliza a
criação do client para uso futuro (cache, blocklist de tokens, rate limit...).
Se `REDIS_ENABLED=false` ou o servidor estiver indisponível, retorna ``None``
e a aplicação continua funcionando normalmente.
"""

from __future__ import annotations

from functools import lru_cache

import redis

from app.core.config import get_settings


@lru_cache
def get_redis() -> redis.Redis | None:
    settings = get_settings()
    if not settings.redis_enabled:
        return None
    try:
        client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        client.ping()
        return client
    except redis.RedisError:
        return None


def redis_health() -> str:
    """Retorna 'disabled', 'ok' ou 'unavailable' (para o endpoint de health)."""
    settings = get_settings()
    if not settings.redis_enabled:
        return "disabled"
    return "ok" if get_redis() is not None else "unavailable"
