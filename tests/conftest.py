"""Configuração dos testes: banco SQLite temporário + cliente autenticado."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def client():
    # Banco isolado por sessão de testes, antes de importar a aplicação.
    db_path = Path(tempfile.gettempdir()) / "sac_progestao_pytest.db"
    if db_path.exists():
        db_path.unlink()
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    os.environ["REDIS_ENABLED"] = "false"

    from fastapi.testclient import TestClient

    from app.db.seed import seed
    from app.main import app

    seed()
    with TestClient(app) as test_client:
        yield test_client

    # Libera o engine antes de remover o arquivo (Windows mantém lock).
    from app.db.base import engine

    engine.dispose()
    try:
        db_path.unlink(missing_ok=True)
    except PermissionError:
        pass


@pytest.fixture(scope="session")
def auth_headers(client):
    resp = client.post(
        "/api/auth/login",
        json={"email": "admin@fumpres.ba.gov.br", "senha": "Demo@2026!"},
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
