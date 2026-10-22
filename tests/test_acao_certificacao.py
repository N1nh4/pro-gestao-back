"""Testes de níveis, certificações, auditorias e ações do plano."""

from datetime import date, timedelta


def _login(client, email: str) -> dict:
    resp = client.post("/api/auth/login", json={"email": email, "senha": "Demo@2026!"})
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _item_da_auditoria(client, headers, auditoria: dict) -> tuple[dict, dict]:
    """Primeiro requisito/item do manual da auditoria."""
    reqs = client.get(
        "/api/catalogo/requisitos",
        headers=headers,
        params={"id_manual": auditoria["id_manual"]},
    ).json()
    for req in reqs:
        itens = client.get(
            "/api/catalogo/itens",
            headers=headers,
            params={"id_requisito": req["id_requisito"]},
        ).json()
        if itens:
            return req, itens[0]
    raise AssertionError("Nenhum item para a auditoria")


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


def test_nao_remover_nivel_com_itens(client, auth_headers):
    niveis = client.get("/api/catalogo/niveis", headers=auth_headers).json()
    id_nivel = niveis[0]["id_nivel"]
    resp = client.delete(f"/api/catalogo/niveis/{id_nivel}", headers=auth_headers)
    assert resp.status_code == 409
    assert "itens" in resp.json()["detail"].lower()


# ── CERTIFICAÇÕES (certificado do ente) ──────────────────────────


def test_listar_e_obter_certificacao(client, auth_headers):
    resp = client.get("/api/certificacoes", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    certs = resp.json()
    assert len(certs) == 1
    cert = certs[0]
    assert cert["nome_certificacao"] == "Certificação Pró-Gestão RPPS"
    assert cert["status"] == "VENCIDA"
    assert cert["numero_certificado"] == "CERT-III-2024-0042"
    assert cert["auditorias_count"] == 4
    assert cert["acoes_count"] > 0

    detalhe = client.get(
        f"/api/certificacoes/{cert['id_certificacao']}", headers=auth_headers
    )
    assert detalhe.status_code == 200, detalhe.text
    assert detalhe.json()["auditorias_count"] == 4


def test_criar_certificacao_e_rejeitar_duplicidade(client, auth_headers):
    # Nome duplicado no mesmo ente.
    resp = client.post(
        "/api/certificacoes",
        headers=auth_headers,
        json={"nome_certificacao": "Certificação Pró-Gestão RPPS"},
    )
    assert resp.status_code == 409

    # Status inválido.
    resp = client.post(
        "/api/certificacoes",
        headers=auth_headers,
        json={"nome_certificacao": "Certificação inválida", "status": "QUALQUER"},
    )
    assert resp.status_code == 422


def test_atualizar_e_remover_certificacao(client, auth_headers):
    resp = client.post(
        "/api/certificacoes",
        headers=auth_headers,
        json={"nome_certificacao": "Certificação temporária"},
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


def test_nao_remover_certificacao_com_auditorias(client, auth_headers):
    cert = client.get("/api/certificacoes", headers=auth_headers).json()[0]
    resp = client.delete(
        f"/api/certificacoes/{cert['id_certificacao']}", headers=auth_headers
    )
    assert resp.status_code == 409
    assert "auditoria" in resp.json()["detail"].lower()


# ── AUDITORIAS (certificação + manual) ───────────────────────────


def test_listar_auditorias_com_nomes_por_join(client, auth_headers):
    resp = client.get("/api/auditorias", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    auds = resp.json()
    assert len(auds) == 4
    assert {a["tipo"] for a in auds} == {
        "auditoria_inicial",
        "supervisao_documental",
        "supervisao_presencial",
        "renovacao",
    }
    assert all(a["nome_manual"] == "Manual do Pró-Gestão RPPS" for a in auds)
    assert all(a["versao_manual"] == "4.1" for a in auds)
    assert all(a["nome_certificacao"] == "Certificação Pró-Gestão RPPS" for a in auds)
    assert all(a["id_certificacao"] > 0 for a in auds)
    assert any(a["acoes_count"] > 0 for a in auds)


def test_criar_auditoria_valida_dependencias(client, auth_headers):
    cert = client.get("/api/certificacoes", headers=auth_headers).json()[0]
    manuais = client.get("/api/catalogo/manuais", headers=auth_headers).json()

    base = {
        "id_certificacao": cert["id_certificacao"],
        "id_manual": manuais[0]["id_manual"],
        "data_auditoria": "2026-10-01",
        "auditor_nome": "Dr. Teste",
    }

    assert (
        client.post(
            "/api/auditorias", headers=auth_headers, json={**base, "id_certificacao": 999999}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/auditorias", headers=auth_headers, json={**base, "id_manual": 999999}
        ).status_code
        == 422
    )

    criada = client.post("/api/auditorias", headers=auth_headers, json=base)
    assert criada.status_code == 201, criada.text
    id_aud = criada.json()["id"]
    assert criada.json()["acoes_count"] == 0

    assert client.get(f"/api/auditorias/{id_aud}", headers=auth_headers).status_code == 200
    assert client.delete(f"/api/auditorias/{id_aud}", headers=auth_headers).status_code == 204


def test_atualizar_auditoria(client, auth_headers):
    aud = next(
        a for a in client.get("/api/auditorias", headers=auth_headers).json()
        if a["acoes_count"] == 0
    )
    resp = client.put(
        f"/api/auditorias/{aud['id']}",
        headers=auth_headers,
        json={"parecer_geral": "Parecer revisado", "conclusao": "aprovado"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["parecer_geral"] == "Parecer revisado"
    assert resp.json()["conclusao"] == "aprovado"


def test_nao_alterar_escopo_de_auditoria_com_acoes(client, auth_headers):
    aud = next(
        a for a in client.get("/api/auditorias", headers=auth_headers).json()
        if a["acoes_count"] > 0
    )
    outro = client.post(
        "/api/catalogo/manuais",
        headers=auth_headers,
        json={"nome_manual": "Manual de teste", "versao_manual": "1.0"},
    )
    assert outro.status_code == 201, outro.text
    id_outro_manual = outro.json()["id_manual"]

    try:
        resp = client.put(
            f"/api/auditorias/{aud['id']}",
            headers=auth_headers,
            json={"id_manual": id_outro_manual},
        )
        assert resp.status_code == 409
        assert "ações" in resp.json()["detail"]
    finally:
        assert (
            client.delete(
                f"/api/catalogo/manuais/{id_outro_manual}", headers=auth_headers
            ).status_code
            == 204
        )

    remover = client.delete(f"/api/auditorias/{aud['id']}", headers=auth_headers)
    assert remover.status_code == 409


# ── AÇÕES (tabela única, dentro da auditoria) ────────────────────


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
    assert primeiro["id_auditoria"]
    assert primeiro["nome_certificacao"] != ""
    assert primeiro["nome_nivel"] != ""
    assert primeiro["historico"] is not None


def test_criar_acao_uma_por_unidade(client, auth_headers):
    acao_base = client.get("/api/acoes", headers=auth_headers).json()[0]
    aud = client.get(
        f"/api/auditorias/{acao_base['id_auditoria']}", headers=auth_headers
    ).json()
    req, item = _item_da_auditoria(client, auth_headers, aud)
    unidades = client.get("/api/unidades", headers=auth_headers).json()

    payload = {
        "id_auditoria": aud["id"],
        "id_requisito": req["id_requisito"],
        "id_item": item["id_item"],
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
    assert criadas[0]["id_auditoria"] == aud["id"]

    for criada in criadas:
        assert (
            client.delete(f"/api/acoes/{criada['id_acao']}", headers=auth_headers).status_code
            == 204
        )


def test_criar_acao_valida_relacoes(client, auth_headers):
    acao = client.get("/api/acoes", headers=auth_headers).json()[0]
    aud = client.get(f"/api/auditorias/{acao['id_auditoria']}", headers=auth_headers).json()
    req, item = _item_da_auditoria(client, auth_headers, aud)

    payload = {
        "id_auditoria": aud["id"],
        "id_requisito": req["id_requisito"],
        "id_item": item["id_item"],
        "nome": "Ação de teste",
        "descricao": "Descrição da ação de teste",
        "prazo": (date.today() + timedelta(days=30)).isoformat(),
        "unidade_ids": [acao["id_unidade"]],
    }
    resp = client.post("/api/acoes", headers=auth_headers, json=payload)
    assert resp.status_code == 201, resp.text
    id_acao = resp.json()[0]["id_acao"]

    try:
        # Item de outro requisito é rejeitado (FK composta).
        outro_req = client.get(
            "/api/catalogo/requisitos", headers=auth_headers, params={"id_manual": aud["id_manual"]}
        ).json()
        outro_id_req = next(
            r["id_requisito"] for r in outro_req if r["id_requisito"] != req["id_requisito"]
        )
        itens_outro = client.get(
            "/api/catalogo/itens", headers=auth_headers, params={"id_requisito": outro_id_req}
        ).json()
        resp = client.post(
            "/api/acoes",
            headers=auth_headers,
            json={**payload, "id_item": itens_outro[0]["id_item"]},
        )
        assert resp.status_code == 422

        # Requisito inexistente
        resp = client.post(
            "/api/acoes", headers=auth_headers, json={**payload, "id_requisito": 999999}
        )
        assert resp.status_code == 422

        # Auditoria inexistente
        resp = client.post(
            "/api/acoes",
            headers=auth_headers,
            json={**payload, "id_auditoria": "00000000-0000-0000-0000-000000000000"},
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
        assert upd.json()["cod_requisito"] == req["cod_requisito"]
    finally:
        assert client.delete(f"/api/acoes/{id_acao}", headers=auth_headers).status_code == 204

    assert client.get(f"/api/acoes/{id_acao}", headers=auth_headers).status_code == 404


def test_upload_comprovacao_transiciona_acao_e_permite_revisao(client, auth_headers):
    operador_headers = _login(client, "operador@fumpres.ba.gov.br")
    acao_base = client.get("/api/acoes", headers=auth_headers).json()[0]
    aud = client.get(
        f"/api/auditorias/{acao_base['id_auditoria']}", headers=auth_headers
    ).json()
    req, item = _item_da_auditoria(client, auth_headers, aud)

    payload = {
        "id_auditoria": aud["id"],
        "id_requisito": req["id_requisito"],
        "id_item": item["id_item"],
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
            "id_auditoria": acoes[0]["id_auditoria"],
            "id_requisito": acoes[0]["id_requisito"],
            "id_item": acoes[0]["id_item"],
            "nome": "X",
            "descricao": "Y",
            "prazo": "2026-12-31",
            "unidade_ids": [acoes[0]["id_unidade"]],
        },
    )
    assert resp.status_code == 403


def test_acao_exige_perfil_admin_para_auditoria(client):
    headers = _login(client, "viewer@previc.gov.br")
    resp = client.post(
        "/api/certificacoes",
        headers=headers,
        json={"nome_certificacao": "Sem permissão"},
    )
    assert resp.status_code == 403
