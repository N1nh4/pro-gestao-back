"""Testes dos níveis, das certificações (tabela única) e das ações do plano."""

from datetime import date, timedelta


def _login(client, email: str) -> dict:
    resp = client.post("/api/auth/login", json={"email": email, "senha": "Demo@2026!"})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# ── NÍVEIS ───────────────────────────────────────────────────────


def test_listar_niveis(client, auth_headers):
    resp = client.get("/api/catalogo/niveis", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    nomes = [n["nome_nivel"] for n in resp.json()]
    assert nomes == ["I", "II", "III", "IV"]


def test_criar_nivel_e_rejeitar_duplicado(client, auth_headers):
    resp = client.post(
        "/api/catalogo/niveis", headers=auth_headers, json={"nome_nivel": "V"}
    )
    assert resp.status_code == 201, resp.text
    id_nivel = resp.json()["id_nivel"]

    dup = client.post("/api/catalogo/niveis", headers=auth_headers, json={"nome_nivel": "V"})
    assert dup.status_code == 409

    upd = client.put(
        f"/api/catalogo/niveis/{id_nivel}", headers=auth_headers, json={"nome_nivel": "V"}
    )
    assert upd.status_code == 200
    assert upd.json()["nome_nivel"] == "V"

    assert client.delete(f"/api/catalogo/niveis/{id_nivel}", headers=auth_headers).status_code == 204


def test_nao_remover_nivel_com_certificacao(client, auth_headers):
    niveis = client.get("/api/catalogo/niveis", headers=auth_headers).json()
    id_nivel = niveis[0]["id_nivel"]
    resp = client.delete(f"/api/catalogo/niveis/{id_nivel}", headers=auth_headers)
    assert resp.status_code == 409
    assert "certifica" in resp.json()["detail"].lower()


# ── CERTIFICAÇÕES (ente + manual + nível) ────────────────────────


def test_listar_certificacoes_com_nomes_por_join(client, auth_headers):
    manuais = client.get("/api/catalogo/manuais", headers=auth_headers).json()
    id_manual = manuais[0]["id_manual"]

    resp = client.get(
        "/api/certificacoes", headers=auth_headers, params={"id_manual": id_manual}
    )
    assert resp.status_code == 200, resp.text
    certs = resp.json()
    assert len(certs) == 4
    assert {c["nome_nivel"] for c in certs} == {"I", "II", "III", "IV"}
    # Nome do manual e do nível vêm por JOIN, não são denormalizados.
    assert all(c["nome_manual"] == manuais[0]["nome_manual"] for c in certs)
    assert all(c["versao_manual"] == manuais[0]["versao_manual"] for c in certs)
    assert all(c["id_certificacao"] > 0 for c in certs)


def test_criar_certificacao_valida_dependencias(client, auth_headers):
    manuais = client.get("/api/catalogo/manuais", headers=auth_headers).json()
    id_manual = manuais[0]["id_manual"]
    niveis = client.get("/api/catalogo/niveis", headers=auth_headers).json()

    # Manual inexistente
    resp = client.post(
        "/api/certificacoes",
        headers=auth_headers,
        json={
            "id_manual": 999999,
            "id_nivel": niveis[0]["id_nivel"],
            "nome_certificacao": "Inválida",
        },
    )
    assert resp.status_code == 422

    # Nível inexistente
    resp = client.post(
        "/api/certificacoes",
        headers=auth_headers,
        json={
            "id_manual": id_manual,
            "id_nivel": 999999,
            "nome_certificacao": "Inválida",
        },
    )
    assert resp.status_code == 422

    # Duplicidade (ente + manual + nível já cadastrado pelo seed)
    resp = client.post(
        "/api/certificacoes",
        headers=auth_headers,
        json={
            "id_manual": id_manual,
            "id_nivel": niveis[0]["id_nivel"],
            "nome_certificacao": "Duplicada",
        },
    )
    assert resp.status_code == 409


def test_atualizar_e_remover_certificacao(client, auth_headers):
    manuais = client.get("/api/catalogo/manuais", headers=auth_headers).json()
    id_manual = manuais[0]["id_manual"]
    niveis = client.get("/api/catalogo/niveis", headers=auth_headers).json()

    resp = client.post(
        "/api/certificacoes",
        headers=auth_headers,
        json={
            "id_manual": id_manual,
            "id_nivel": niveis[0]["id_nivel"],
            "nome_certificacao": "Certificação temporária",
        },
    )
    assert resp.status_code == 409  # já existe para o nível

    # Usa outro manual (sem certificações) para o ciclo completo.
    resp = client.post(
        "/api/catalogo/manuais",
        headers=auth_headers,
        json={"nome_manual": "Manual de teste", "versao_manual": "9.9"},
    )
    assert resp.status_code == 201, resp.text
    id_manual_novo = resp.json()["id_manual"]

    resp = client.post(
        "/api/certificacoes",
        headers=auth_headers,
        json={
            "id_manual": id_manual_novo,
            "id_nivel": niveis[0]["id_nivel"],
            "nome_certificacao": "Certificação temporária",
        },
    )
    assert resp.status_code == 201, resp.text
    id_cert = resp.json()["id_certificacao"]

    upd = client.put(
        f"/api/certificacoes/{id_cert}",
        headers=auth_headers,
        json={
            "nome_certificacao": "Certificação renomeada",
            "status": "VIGENTE",
            "numero_certificado": "CERT-9.9-0001",
        },
    )
    assert upd.status_code == 200, upd.text
    assert upd.json()["nome_certificacao"] == "Certificação renomeada"
    assert upd.json()["status"] == "VIGENTE"
    assert upd.json()["numero_certificado"] == "CERT-9.9-0001"

    # Status inválido
    resp = client.put(
        f"/api/certificacoes/{id_cert}", headers=auth_headers, json={"status": "QUALQUER"}
    )
    assert resp.status_code == 422

    assert (
        client.delete(f"/api/certificacoes/{id_cert}", headers=auth_headers).status_code == 204
    )
    assert (
        client.delete(f"/api/catalogo/manuais/{id_manual_novo}", headers=auth_headers).status_code
        == 204
    )


# ── AÇÕES (tabela única) ──────────────────────────────────────────


def test_listar_acoes_com_nomes_por_join(client, auth_headers):
    resp = client.get("/api/acoes", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    acoes = resp.json()
    assert len(acoes) >= 4
    primeiro = acoes[0]
    assert isinstance(primeiro["id_acao"], int)
    assert primeiro["id_acao"] > 0
    assert primeiro["cod_requisito"] != ""
    assert primeiro["sigla_unidade"] != ""
    assert primeiro["id_requisito"] > 0
    assert primeiro["id_certificacao"] > 0
    assert primeiro["nome_certificacao"] != ""
    assert primeiro["historico"] is not None


def test_criar_acao_uma_por_unidade(client, auth_headers):
    reqs = client.get("/api/catalogo/requisitos", headers=auth_headers).json()
    id_requisito = reqs[0]["id_requisito"]
    itens = client.get(
        "/api/catalogo/itens", headers=auth_headers, params={"id_requisito": id_requisito}
    ).json()
    unidades = client.get("/api/unidades", headers=auth_headers).json()

    payload = {
        "id_requisito": id_requisito,
        "id_item": itens[0]["id_item"],
        "nome": "Ação de teste",
        "descricao": "Descrição da ação de teste",
        "prazo": (date.today() + timedelta(days=30)).isoformat(),
        "unidade_ids": [unidades[0]["id"], unidades[1]["id"]],
    }
    resp = client.post("/api/acoes", headers=auth_headers, json=payload)
    assert resp.status_code == 201, resp.text
    criadas = resp.json()
    assert len(criadas) == 2
    assert criadas[0]["id_acao"] != criadas[1]["id_acao"]
    assert criadas[0]["id_unidade"] == unidades[0]["id"]
    assert criadas[1]["id_unidade"] == unidades[1]["id"]
    assert criadas[0]["status"] == "PENDENTE"
    # A certificação do ente é resolvida automaticamente (manual + nível do item).
    assert criadas[0]["id_certificacao"] > 0

    for criada in criadas:
        assert (
            client.delete(f"/api/acoes/{criada['id_acao']}", headers=auth_headers).status_code
            == 204
        )


def test_criar_acao_valida_relacoes(client, auth_headers):
    acoes = client.get("/api/acoes", headers=auth_headers).json()
    acao = acoes[0]
    itens = client.get(
        "/api/catalogo/itens", headers=auth_headers, params={"id_requisito": acao["id_requisito"]}
    ).json()

    payload = {
        "id_requisito": acao["id_requisito"],
        "id_item": itens[0]["id_item"],
        "nome": "Ação de teste",
        "descricao": "Descrição da ação de teste",
        "prazo": (date.today() + timedelta(days=30)).isoformat(),
        "unidade_ids": [acao["id_unidade"]],
    }
    resp = client.post("/api/acoes", headers=auth_headers, json=payload)
    assert resp.status_code == 201, resp.text
    id_acao = resp.json()[0]["id_acao"]

    # Item de outro requisito é rejeitado (FK composta).
    outro_req = client.get(
        "/api/catalogo/requisitos", headers=auth_headers, params={"id_manual": 1}
    ).json()
    outro_id_req = next(
        r["id_requisito"] for r in outro_req if r["id_requisito"] != acao["id_requisito"]
    )
    itens_outro = client.get(
        "/api/catalogo/itens", headers=auth_headers, params={"id_requisito": outro_id_req}
    ).json()
    resp = client.post(
        "/api/acoes", headers=auth_headers, json={**payload, "id_item": itens_outro[0]["id_item"]}
    )
    assert resp.status_code == 422

    # Requisito inexistente
    resp = client.post(
        "/api/acoes", headers=auth_headers, json={**payload, "id_requisito": 999999}
    )
    assert resp.status_code == 422

    # Status inválido
    resp = client.post(
        "/api/acoes", headers=auth_headers, json={**payload, "status": "XYZ"}
    )
    assert resp.status_code == 422

    # O status ENVIADO só pode ser definido após o upload da comprovação.
    resp = client.patch(
        f"/api/acoes/{id_acao}/status", headers=auth_headers, json={"status": "ENVIADO"}
    )
    assert resp.status_code == 409
    assert "documento" in resp.json()["detail"]

    # Edição mantém o registro e os nomes resolvidos por JOIN.
    upd = client.put(
        f"/api/acoes/{id_acao}",
        headers=auth_headers,
        json={"nome": "Ação editada", "descricao": "Descrição editada"},
    )
    assert upd.status_code == 200, upd.text
    assert upd.json()["nome"] == "Ação editada"
    assert upd.json()["cod_requisito"] == acao["cod_requisito"]

    assert client.delete(f"/api/acoes/{id_acao}", headers=auth_headers).status_code == 204
    assert client.get(f"/api/acoes/{id_acao}", headers=auth_headers).status_code == 404


def test_upload_comprovacao_transiciona_acao_e_permite_revisao(client, auth_headers):
    operador_headers = _login(client, "operador@fumpres.ba.gov.br")
    acao_base = client.get("/api/acoes", headers=auth_headers).json()[0]
    itens = client.get(
        "/api/catalogo/itens",
        headers=auth_headers,
        params={"id_requisito": acao_base["id_requisito"]},
    ).json()
    payload = {
        "id_requisito": acao_base["id_requisito"],
        "id_item": itens[0]["id_item"],
        "nome": "Ação com comprovação",
        "descricao": "Ação usada para validar o envio de documento",
        "prazo": (date.today() + timedelta(days=30)).isoformat(),
        "unidade_ids": ["un04"],
    }
    criada = client.post("/api/acoes", headers=auth_headers, json=payload)
    assert criada.status_code == 201, criada.text
    id_acao = criada.json()[0]["id_acao"]

    proibido = client.post(
        f"/api/acoes/{id_acao}/documentos",
        headers=auth_headers,
        files={"arquivo": ("comprovacao.pdf", b"%PDF-test", "application/pdf")},
    )
    assert proibido.status_code == 403

    invalido = client.post(
        f"/api/acoes/{id_acao}/documentos",
        headers=operador_headers,
        files={"arquivo": ("comprovacao.txt", b"conteudo", "text/plain")},
    )
    assert invalido.status_code == 422

    enviado = client.post(
        f"/api/acoes/{id_acao}/documentos",
        headers=operador_headers,
        files={"arquivo": ("comprovacao.pdf", b"%PDF-test", "application/pdf")},
    )
    assert enviado.status_code == 201, enviado.text
    documento = enviado.json()
    assert documento["versao"] == 1

    acao = client.get(f"/api/acoes/{id_acao}", headers=auth_headers)
    assert acao.status_code == 200, acao.text
    assert acao.json()["status"] == "ENVIADO"
    assert len(acao.json()["documentos"]) == 1

    diligencia = client.post(
        "/api/diligencias",
        headers=auth_headers,
        json={
            "acao_id": id_acao,
            "situacao_detectada": "Complementar a comprovação",
            "criticidade": "media",
            "prazo_resposta": (date.today() + timedelta(days=15)).isoformat(),
        },
    )
    assert diligencia.status_code == 200, diligencia.text
    assert client.get(f"/api/acoes/{id_acao}", headers=auth_headers).json()["status"] == "DILIGÊNCIA"

    reenviado = client.post(
        f"/api/acoes/{id_acao}/documentos",
        headers=operador_headers,
        files={"arquivo": ("comprovacao-revisada.pdf", b"%PDF-revised", "application/pdf")},
    )
    assert reenviado.status_code == 201, reenviado.text
    assert reenviado.json()["versao"] == 2

    aprovado = client.patch(
        f"/api/acoes/{id_acao}/status", headers=auth_headers, json={"status": "APROVADO"}
    )
    assert aprovado.status_code == 200, aprovado.text
    assert aprovado.json()["status"] == "APROVADO"

    download = client.get(
        f"/api/acoes/{id_acao}/documentos/{documento['id']}",
        headers=auth_headers,
    )
    assert download.status_code == 200
    assert download.content == b"%PDF-test"

    assert client.delete(f"/api/acoes/{id_acao}", headers=auth_headers).status_code == 204


def test_acao_exige_perfil_admin(client):
    headers = _login(client, "viewer@previc.gov.br")
    resp = client.get("/api/acoes", headers=headers)
    assert resp.status_code == 200  # leitura liberada

    acoes = client.get("/api/acoes", headers=headers).json()
    resp = client.post(
        "/api/acoes",
        headers=headers,
        json={
            "id_requisito": acoes[0]["id_requisito"],
            "id_item": acoes[0]["id_item"],
            "nome": "X",
            "descricao": "Y",
            "prazo": "2026-12-31",
            "unidade_ids": [acoes[0]["id_unidade"]],
        },
    )
    assert resp.status_code == 403
