"""CRUD do catálogo do manual: manual, dimensões, requisitos e itens."""

from __future__ import annotations


def test_listar_catalogo_completo(client, auth_headers):
    manuais = client.get("/api/catalogo/manuais", headers=auth_headers).json()
    assert len(manuais) == 1
    assert manuais[0]["versao_manual"] == "4.1"

    dimensoes = client.get("/api/catalogo/dimensoes", headers=auth_headers).json()
    assert len(dimensoes) == 3

    requisitos = client.get("/api/catalogo/requisitos", headers=auth_headers).json()
    assert len(requisitos) == 24
    # O requisito 3.1.1 tem 22 itens no catálogo carregado.
    r311 = next(r for r in requisitos if r["cod_requisito"] == "3.1.1")
    assert r311["total_itens"] == 22
    assert r311["nome_dimensao"] == "Controles Internos"

    itens = client.get(
        "/api/catalogo/itens", headers=auth_headers, params={"id_requisito": r311["id_requisito"]}
    ).json()
    assert len(itens) == 22
    assert {i["nivel"] for i in itens} <= {"I", "II", "III", "IV"}


def test_filtrar_requisitos_por_dimensao(client, auth_headers):
    dimensoes = client.get("/api/catalogo/dimensoes", headers=auth_headers).json()
    ep = next(d for d in dimensoes if d["nome_dimensao"] == "Educação Previdenciária")

    reqs = client.get(
        "/api/catalogo/requisitos",
        headers=auth_headers,
        params={"id_dimensao": ep["id_dimensao"]},
    ).json()
    assert len(reqs) == 2
    assert all(r["cod_requisito"].startswith("3.3") for r in reqs)


def test_criar_atualizar_remover_dimensao(client, auth_headers):
    create = client.post(
        "/api/catalogo/dimensoes",
        headers=auth_headers,
        json={"nome_dimensao": "Teste Dimensão"},
    )
    assert create.status_code == 201, create.text
    id_dim = create.json()["id_dimensao"]

    dup = client.post(
        "/api/catalogo/dimensoes",
        headers=auth_headers,
        json={"nome_dimensao": "Teste Dimensão"},
    )
    assert dup.status_code == 409

    upd = client.put(
        f"/api/catalogo/dimensoes/{id_dim}",
        headers=auth_headers,
        json={"nome_dimensao": "Teste Dimensão 2"},
    )
    assert upd.status_code == 200
    assert upd.json()["nome_dimensao"] == "Teste Dimensão 2"

    delete = client.delete(f"/api/catalogo/dimensoes/{id_dim}", headers=auth_headers)
    assert delete.status_code == 204
    restantes = client.get("/api/catalogo/dimensoes", headers=auth_headers).json()
    assert all(d["id_dimensao"] != id_dim for d in restantes)


def test_nao_remover_dimensao_com_requisitos(client, auth_headers):
    dimensoes = client.get("/api/catalogo/dimensoes", headers=auth_headers).json()
    ci = next(d for d in dimensoes if d["nome_dimensao"] == "Controles Internos")
    resp = client.delete(f"/api/catalogo/dimensoes/{ci['id_dimensao']}", headers=auth_headers)
    assert resp.status_code == 409


def test_criar_requisito_valida_codigo_e_dependencias(client, auth_headers):
    manuais = client.get("/api/catalogo/manuais", headers=auth_headers).json()
    dimensoes = client.get("/api/catalogo/dimensoes", headers=auth_headers).json()
    id_manual = manuais[0]["id_manual"]
    id_dim = dimensoes[0]["id_dimensao"]

    ruim = client.post(
        "/api/catalogo/requisitos",
        headers=auth_headers,
        json={
            "id_manual": id_manual,
            "id_dimensao": id_dim,
            "cod_requisito": "abc",
            "nome_requisito": "Código inválido",
        },
    )
    assert ruim.status_code == 422

    sem_manual = client.post(
        "/api/catalogo/requisitos",
        headers=auth_headers,
        json={
            "id_manual": 99999,
            "id_dimensao": id_dim,
            "cod_requisito": "9.9.9",
            "nome_requisito": "Manual inexistente",
        },
    )
    assert sem_manual.status_code == 422

    ok = client.post(
        "/api/catalogo/requisitos",
        headers=auth_headers,
        json={
            "id_manual": id_manual,
            "id_dimensao": id_dim,
            "cod_requisito": "9.9.1",
            "nome_requisito": "Requisito novo",
        },
    )
    assert ok.status_code == 201, ok.text
    id_req = ok.json()["id_requisito"]

    # Mesmo código no mesmo manual -> conflito.
    dup = client.post(
        "/api/catalogo/requisitos",
        headers=auth_headers,
        json={
            "id_manual": id_manual,
            "id_dimensao": id_dim,
            "cod_requisito": "9.9.1",
            "nome_requisito": "Duplicado",
        },
    )
    assert dup.status_code == 409

    # Mesmo código em outro manual -> permitido.
    outro = client.post(
        "/api/catalogo/manuais",
        headers=auth_headers,
        json={"nome_manual": "Manual Teste", "versao_manual": "9.9"},
    )
    assert outro.status_code == 201, outro.text
    id_outro = outro.json()["id_manual"]

    outro_req = client.post(
        "/api/catalogo/requisitos",
        headers=auth_headers,
        json={
            "id_manual": id_outro,
            "id_dimensao": id_dim,
            "cod_requisito": "9.9.1",
            "nome_requisito": "Mesmo código, outro manual",
        },
    )
    assert outro_req.status_code == 201

    upd = client.put(
        f"/api/catalogo/requisitos/{id_req}",
        headers=auth_headers,
        json={"nome_requisito": "Requisito renomeado"},
    )
    assert upd.status_code == 200
    assert upd.json()["nome_requisito"] == "Requisito renomeado"

    delete = client.delete(f"/api/catalogo/requisitos/{id_req}", headers=auth_headers)
    assert delete.status_code == 204
    assert client.delete(
        f"/api/catalogo/requisitos/{outro_req.json()['id_requisito']}", headers=auth_headers
    ).status_code == 204
    assert client.delete(f"/api/catalogo/manuais/{id_outro}", headers=auth_headers).status_code == 204


def test_criar_item_valida_nivel_e_unicidade(client, auth_headers):
    requisitos = client.get("/api/catalogo/requisitos", headers=auth_headers).json()
    alvo = next(r for r in requisitos if r["cod_requisito"] == "3.2.2")
    id_req = alvo["id_requisito"]

    nivel_ruim = client.post(
        "/api/catalogo/itens",
        headers=auth_headers,
        json={"id_requisito": id_req, "nome_item": "Item X", "nivel": "V"},
    )
    assert nivel_ruim.status_code == 422

    sem_req = client.post(
        "/api/catalogo/itens",
        headers=auth_headers,
        json={"id_requisito": 99999, "nome_item": "Item Y", "nivel": "I"},
    )
    assert sem_req.status_code == 422

    ok = client.post(
        "/api/catalogo/itens",
        headers=auth_headers,
        json={"id_requisito": id_req, "nome_item": "Item Teste", "nivel": "I", "descricao": "d"},
    )
    assert ok.status_code == 201, ok.text
    id_item = ok.json()["id_item"]

    dup = client.post(
        "/api/catalogo/itens",
        headers=auth_headers,
        json={"id_requisito": id_req, "nome_item": "Item Teste", "nivel": "I"},
    )
    assert dup.status_code == 409

    # Mesmo nome em outro nível -> permitido.
    outro_nivel = client.post(
        "/api/catalogo/itens",
        headers=auth_headers,
        json={"id_requisito": id_req, "nome_item": "Item Teste", "nivel": "II"},
    )
    assert outro_nivel.status_code == 201

    upd = client.put(
        f"/api/catalogo/itens/{id_item}",
        headers=auth_headers,
        json={"nome_item": "Item Teste Renomeado"},
    )
    assert upd.status_code == 200
    assert upd.json()["nome_item"] == "Item Teste Renomeado"

    assert client.delete(
        f"/api/catalogo/itens/{id_item}", headers=auth_headers
    ).status_code == 204
    assert client.delete(
        f"/api/catalogo/itens/{outro_nivel.json()['id_item']}", headers=auth_headers
    ).status_code == 204


def test_exige_admin_para_escrita(client, auth_headers):
    # Visualizador não pode escrever no catálogo.
    login = client.post(
        "/api/auth/login",
        json={"email": "viewer@previc.gov.br", "senha": "Demo@2026!"},
    )
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    resp = client.post(
        "/api/catalogo/dimensoes", headers=headers, json={"nome_dimensao": "Bloqueada"}
    )
    assert resp.status_code == 403

    # Leitura continua liberada.
    assert client.get("/api/catalogo/requisitos", headers=headers).status_code == 200
