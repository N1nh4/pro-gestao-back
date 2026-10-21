"""Testes de fumaça: cobrem os fluxos principais da API."""

from __future__ import annotations


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "online"
    assert body["redis"] == "disabled"


def test_login_invalido(client):
    resp = client.post(
        "/api/auth/login",
        json={"email": "admin@fumpres.ba.gov.br", "senha": "errada"},
    )
    assert resp.status_code == 401


def test_requer_token(client):
    resp = client.get("/api/acoes")
    assert resp.status_code == 401


def test_me(client, auth_headers):
    resp = client.get("/api/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "admin@fumpres.ba.gov.br"
    perfis = {p["nome"] for p in resp.json()["perfis"]}
    assert "Admin Master" in perfis


def test_requisitos(client, auth_headers):
    resp = client.get("/api/requisitos", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 24


def test_listar_acoes(client, auth_headers):
    resp = client.get("/api/acoes", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 20


def test_criar_acao_impede_status_enviado_sem_upload(client, auth_headers):
    acoes = client.get("/api/acoes", headers=auth_headers).json()
    base = acoes[0]
    itens = client.get(
        "/api/catalogo/itens", headers=auth_headers, params={"id_requisito": base["id_requisito"]}
    ).json()

    create = client.post(
        "/api/acoes",
        headers=auth_headers,
        json={
            "id_requisito": base["id_requisito"],
            "id_item": itens[0]["id_item"],
            "nome": "Ação de teste",
            "descricao": "Ação de teste",
            "prazo": "2026-12-31",
            "unidade_ids": [base["id_unidade"], acoes[1]["id_unidade"]],
        },
    )
    assert create.status_code == 201, create.text
    criadas = create.json()
    assert len(criadas) == 2
    assert criadas[0]["id_acao"] != criadas[1]["id_acao"]

    patch = client.patch(
        f"/api/acoes/{criadas[0]['id_acao']}/status",
        headers=auth_headers,
        json={"status": "ENVIADO"},
    )
    assert patch.status_code == 409
    assert client.get(f"/api/acoes/{criadas[0]['id_acao']}", headers=auth_headers).json()[
        "status"
    ] == "PENDENTE"

    for criada in criadas:
        assert (
            client.delete(f"/api/acoes/{criada['id_acao']}", headers=auth_headers).status_code
            == 204
        )


def test_bi_consolidado(client, auth_headers):
    resp = client.get("/api/bi/consolidado", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_acoes"] >= 20
    assert set(body["por_dimensao"]) == {"CI", "GC", "EP"}


def test_certificacoes(client, auth_headers):
    resp = client.get("/api/certificacoes", headers=auth_headers)
    assert resp.status_code == 200
    certs = resp.json()
    # Uma certificação por nível do manual, do ente.
    assert len(certs) == 4
    assert {c["nome_nivel"] for c in certs} == {"I", "II", "III", "IV"}


def test_criar_auditoria(client, auth_headers):
    resp = client.post(
        "/api/auditorias",
        headers=auth_headers,
        json={
            "data_auditoria": "2026-10-01",
            "entidade_certificadora": "IEPREV",
            "auditor_nome": "Dr. Teste",
            "conclusao": "aprovado",
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["conclusao"] == "aprovado"


def test_onboarding(client, auth_headers):
    resp = client.get("/api/onboarding/status", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["ente"]["cnpj_ente"] == "12.345.678/0001-90"


def test_diligencias(client, auth_headers):
    resp = client.get("/api/diligencias", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 4
