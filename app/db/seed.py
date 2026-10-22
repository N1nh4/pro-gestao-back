"""Cria a estrutura base do banco (tenant, perfis, páginas, usuários).

Uso:
    python -m app.db.seed           # só estrutura base (banco vazio de negócio)
    python -m app.db.seed --demo    # estrutura base + dados demo do FUMPRES
"""

import sys
from datetime import date

from app.core.security import hash_senha
from app.db.base import Base, SessionLocal, engine

# Importa os modelos para registrar no metadata antes do create_all.
from app.db.catalogo_itens import ITENS_POR_REQUISITO
from app.models import (  # noqa: F401
    Acao,
    Auditoria,
    Certificacao,
    Diligencia,
    Dimensao,
    Evidencia,
    HistoricoAcao,
    Item,
    Manual,
    Nivel,
    Pagina,
    Perfil,
    PerfilPagina,
    ProcessoProgestao,
    Requisito,
    RequisitoUnidade,
    Tarefa,
    Tenant,
    Unidade,
    Usuario,
    UsuarioUnidadePerfil,
)

SENHA_DEMO = "Demo@2026!"


def seed(demo: bool = False) -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Tenant).first():
            print("✓ Banco já populado. Pulando seed.")
            return

        print("⏳ Populando banco de dados (estrutura base)...")

        # ── TENANT ────────────────────────────────────────────────
        tenant = Tenant(
            id="tenant-fumpres-001",
            nome_ente="Fundo Municipal de Previdência Social de Salvador",
            cnpj_ente="12.345.678/0001-90",
            uf="BA",
            tipo_ente="Município",
            nome_ug="FUMPRES",
            cnpj_ug="12.345.678/0001-90",
            nivel_atual="III",
            nivel_pretendido="IV",
            data_adesao=date(2022, 3, 1),
            entidade_certificadora="IEPREV",
            num_segurados=12500,
            email_contato="fumpres@salvador.ba.gov.br",
            representante_legal="Felipe Araújo",
            cpf_representante="123.456.789-00",
            data_inicio_processo=date(2024, 1, 15),
            data_fim_processo=date(2025, 12, 31),
            codigo_siafi="938002",
            cep="40015-970",
            cidade="Salvador",
            tipo_logradouro="Avenida",
            logradouro="Av. Vale dos Barris",
            numero="1055",
            bairro="Barris",
            complemento="Prédio da FUMPRES",
            ativo=True,
        )
        db.add(tenant)
        db.flush()

        # ── PÁGINAS ───────────────────────────────────────────────
        paginas_data = [
            ("pg01", "Painel Executivo", "/painel", "ti-layout-dashboard", 1),
            ("pg02", "Pró-Gestão / Diagnóstico", "/progestao", "ti-clipboard-check", 2),
            ("pg03", "Plano de Ação", "/plano", "ti-list-check", 3),
            ("pg04", "Diligências", "/diligencias", "ti-messages", 4),
            ("pg05", "Central de Certificações", "/certificacoes", "ti-award", 5),
            ("pg06", "BI / Painel Analítico", "/bi", "ti-chart-bar", 6),
            ("pg07", "Configurações", "/config", "ti-settings", 7),
        ]
        for pid, nome, rota, icone, ordem in paginas_data:
            db.add(Pagina(id=pid, nome=nome, rota=rota, icone=icone, ordem=ordem))
        db.flush()

        # ── PERFIS NATIVOS ────────────────────────────────────────
        perfis_data = [
            ("pf01", "Admin Master", "Proprietário do sistema — acesso total irrestrito", False),
            ("pf02", "Admin do Ente", "Administrador do órgão — gerencia usuários e setores", False),
            ("pf03", "Operador", "Responsável pelo upload de comprovações do seu setor", True),
            ("pf04", "Visualizador", "Acesso somente leitura a painéis e relatórios", True),
        ]
        for pid, nome, desc, req_setor in perfis_data:
            db.add(Perfil(id=pid, nome=nome, descricao=desc, tipo="nativo", requer_setor=req_setor))

        db.add(
            Perfil(
                id="pf05",
                nome="Auditor Interno",
                tipo="customizado",
                descricao="Audita, valida e emite diligências por requisito",
                requer_setor=False,
                tenant_id=tenant.id,
            )
        )
        db.flush()

        # ── PERMISSÕES por Perfil/Página ──────────────────────────
        def add_perm(perfil_id, pagina_id, vis=True, cri=False, edi=False, apr=False, exc=False, exp=False):
            db.add(
                PerfilPagina(
                    perfil_id=perfil_id,
                    pagina_id=pagina_id,
                    pode_visualizar=vis,
                    pode_criar=cri,
                    pode_editar=edi,
                    pode_aprovar=apr,
                    pode_excluir=exc,
                    pode_exportar=exp,
                )
            )

        for pg in ["pg01", "pg02", "pg03", "pg04", "pg05", "pg06"]:
            add_perm("pf02", pg, vis=True, cri=True, edi=True, apr=True, exp=True)
        add_perm("pf02", "pg07", vis=True, cri=True, edi=True)
        add_perm("pf03", "pg01", vis=True)
        add_perm("pf03", "pg02", vis=True)
        add_perm("pf03", "pg03", vis=True, cri=True, edi=True)
        add_perm("pf03", "pg04", vis=True, edi=True)
        for pg in ["pg01", "pg02", "pg05", "pg06"]:
            add_perm("pf04", pg, vis=True, exp=True)
        for pg in ["pg01", "pg02", "pg03", "pg04", "pg05", "pg06"]:
            add_perm("pf05", pg, vis=True, cri=True, edi=True, apr=True, exp=True)
        db.flush()

        # ── USUÁRIOS ──────────────────────────────────────────────
        senha = hash_senha(SENHA_DEMO)
        usuarios_data = [
            ("u001", "001", "felipe.araujo", "admin@fumpres.ba.gov.br", "Felipe Araújo"),
            ("u002", "002", "joao.silva", "auditor@fumpres.ba.gov.br", "João Silva"),
            ("u003", "003", "maria.costa", "operador@fumpres.ba.gov.br", "Maria Costa"),
            ("u004", "004", "pedro.lima", "viewer@previc.gov.br", "Pedro Lima"),
        ]
        for uid, seq, login, email, nome in usuarios_data:
            db.add(
                Usuario(
                    id=uid,
                    id_usuario=seq,
                    tenant_id=tenant.id,
                    login=login,
                    email=email,
                    nome_completo=nome,
                    senha_hash=senha,
                    status="ativo",
                    criado_por=None,
                )
            )
        db.flush()

        # ── VÍNCULOS USUARIO-PERFIL (estrutura base) ──────────────
        vinculos_base = [
            ("u001", "pf01"),
            ("u002", "pf02"),
            ("u002", "pf05"),
            ("u003", "pf03"),
            ("u004", "pf04"),
        ]
        for uid, pid in vinculos_base:
            db.add(
                UsuarioUnidadePerfil(
                    usuario_id=uid, unidade_id=None, perfil_id=pid, concedido_por="u001"
                )
            )
        db.flush()

        # ── NÍVEIS DE CERTIFICAÇÃO (I–IV) ─────────────────────────
        # Domínio fixo do Pró-Gestão: todo manual oferece um nível de cada vez.
        for nome in ("I", "II", "III", "IV"):
            db.add(Nivel(nome_nivel=nome))
        db.flush()

        # ── MANUAL 4.1 + DIMENSÕES + REQUISITOS + ITENS ───────────
        # Catálogo de referência (vale para todo tenant), não dado de negócio.
        # A tabela `requisito` guarda só os IDs (manual/dimensão); o nome da
        # dimensão e do manual vêm por JOIN. Itens por nível (I–IV) saem de
        # `app.db.catalogo_itens`.
        manual = Manual(
            nome_manual="Manual do Pró-Gestão RPPS",
            versao_manual="4.1",
        )
        db.add(manual)
        db.flush()

        # Certificado do ente (um por ente). As auditorias ficam dentro dele.
        cert = Certificacao(
            tenant_id=tenant.id,
            nome_certificacao="Certificação Pró-Gestão RPPS",
            status="PENDENTE",
        )
        db.add(cert)
        db.flush()

        dims = {
            "3.1": Dimensao(nome_dimensao="Controles Internos"),
            "3.2": Dimensao(nome_dimensao="Governança Corporativa"),
            "3.3": Dimensao(nome_dimensao="Educação Previdenciária"),
        }
        for d in dims.values():
            db.add(d)
        db.flush()

        # (cod, nome_requisito) — a dimensão sai do prefixo do cod.
        reqs_data = [
            ("3.1.1", "Mapeamento das Atividades das Áreas de Atuação do RPPS"),
            ("3.1.2", "Manualização das Atividades das Áreas de Atuação do RPPS"),
            ("3.1.3", "Certificação dos Dirigentes, Membros dos Conselhos Deliberativo e Fiscal, do Responsável pela Gestão das aplicações dos Recursos e Membros do Comitê de Investimentos"),
            ("3.1.4", "Estrutura de Controle Interno"),
            ("3.1.5", "Política de Segurança da Informação"),
            ("3.1.6", "Gestão e Controle da Base de Dados Cadastrais dos Servidores Públicos, Aposentados e Pensionistas"),
            ("3.2.1", "Relatório de Governança Corporativa"),
            ("3.2.2", "Planejamento"),
            ("3.2.3", "Relatório de Gestão Atuarial"),
            ("3.2.4", "Código de Ética"),
            ("3.2.5", "Políticas Previdenciárias de Saúde e Segurança do Servidor e Revisão de Aposentadoria por Incapacidade"),
            ("3.2.6", "Política de Investimentos"),
            ("3.2.7", "Comitê de Investimentos"),
            ("3.2.8", "Transparência"),
            ("3.2.9", "Definição de Limites de Alçadas"),
            ("3.2.10", "Segregação das Atividades"),
            ("3.2.11", "Ouvidoria"),
            ("3.2.12", "Diretoria Executiva"),
            ("3.2.13", "Conselho Fiscal"),
            ("3.2.14", "Conselho Deliberativo"),
            ("3.2.15", "Mandato, Representação e Recondução"),
            ("3.2.16", "Gestão de Pessoas"),
            ("3.3.1", "Plano de Ação de Capacitação"),
            ("3.3.2", "Ações de Diálogo com os Segurados e a Sociedade"),
        ]
        req_id_por_cod: dict[str, int] = {}
        for cod, nome in reqs_data:
            req = Requisito(
                id_manual=manual.id_manual,
                id_dimensao=dims[cod.rsplit(".", 1)[0]].id_dimensao,
                cod_requisito=cod,
                nome_requisito=nome,
            )
            db.add(req)
            db.flush()
            req_id_por_cod[cod] = req.id_requisito

        for cod, itens in ITENS_POR_REQUISITO.items():
            rid = req_id_por_cod.get(cod)
            if rid is None:
                continue
            for nivel, nome_item, descricao in itens:
                db.add(
                    Item(
                        id_requisito=rid,
                        nome_item=nome_item,
                        nivel=nivel,
                        descricao=descricao,
                    )
                )
        db.flush()

        # Itens de cada requisito (id, nível) — as ações do plano apontam por ID.
        itens_por_cod: dict[str, list[tuple[int, str]]] = {}
        for cod, rid in req_id_por_cod.items():
            itens = (
                db.query(Item)
                .filter(Item.id_requisito == rid)
                .order_by(Item.nivel, Item.id_item)
                .all()
            )
            if itens:
                itens_por_cod[cod] = [(i.id_item, i.nivel) for i in itens]

        if not demo:
            db.commit()
            print("✅ Estrutura base criada (sem dados de negócio).")
            print_credenciais()
            return

        # ── AUDITORIAS (histórico do manual 4.1) ──────────────────
        # A auditoria é a dona do plano: escolhe o manual e guarda as ações.
        # Todas pertencem ao mesmo certificado do ente; o nível é do item.
        auditorias_demo = [
            ("auditoria_inicial", "presencial", date(2024, 6, 1), "II", "aprovado"),
            ("supervisao_documental", "remota", date(2025, 6, 1), "III", "aprovado"),
            (
                "supervisao_presencial",
                "presencial",
                date(2026, 1, 15),
                "III",
                "aprovado_ressalvas",
            ),
            ("renovacao", "presencial", date(2026, 6, 1), "IV", "pendente"),
        ]
        auditoria_atual: Auditoria | None = None
        for tipo, modalidade, data_auditoria, recomendado, conclusao in auditorias_demo:
            aud = Auditoria(
                tenant_id=tenant.id,
                id_certificacao=cert.id_certificacao,
                id_manual=manual.id_manual,
                tipo=tipo,
                modalidade=modalidade,
                data_auditoria=data_auditoria,
                duracao_horas=8.0,
                nivel_recomendado=recomendado,
                conclusao=conclusao,
                auditor_nome="Auditor IEPREV",
                criado_por="u001",
            )
            db.add(aud)
            auditoria_atual = aud
        db.flush()

        # ── UNIDADES ──────────────────────────────────────────────
        unidades_data = UNIDADES_DEMO
        for uid, sigla, nome in unidades_data:
            db.add(Unidade(id=uid, tenant_id=tenant.id, sigla=sigla, nome=nome, criado_por="u002"))
        db.flush()

        # ── VÍNCULOS USUARIO-UNIDADE-PERFIL ───────────────────────
        db.query(UsuarioUnidadePerfil).delete()
        db.flush()
        vinculos = [
            ("u001", None, "pf01"),
            ("u002", None, "pf02"),
            ("u002", None, "pf05"),
            ("u003", "un04", "pf03"),
            ("u004", "un02", "pf04"),
        ]
        for uid, unid, pid in vinculos:
            db.add(
                UsuarioUnidadePerfil(
                    usuario_id=uid, unidade_id=unid, perfil_id=pid, concedido_por="u001"
                )
            )
        db.flush()

        req_unid_map = {
            "3.1.1": ["un01", "un04", "un05", "un02", "un10", "un07", "un08"],
            "3.1.3": ["un01", "un08"],
            "3.2.2": ["un01", "un04"],
            "3.2.8": ["un06"],
            "3.3.1": ["un03", "un01"],
        }
        for req_cod, uids in req_unid_map.items():
            for uid in uids:
                db.add(
                    RequisitoUnidade(
                        requisito_id=req_id_por_cod[req_cod], unidade_id=uid
                    )
                )
        db.flush()

        # ── AÇÕES (tabela única `acao`) ───────────────────────────
        # Tudo por ID: certificação (ente + manual), requisito, item
        # e unidade. O planejamento (o quê, por quem, até quando) faz parte do
        # próprio registro da ação.
        # (chave demo, requisito, nome, descrição, unidade, status, prazo, envio)
        acoes_data = ACORES_DEMO
        acao_id_por_chave: dict[str, int] = {}
        item_por_requisito: dict[str, int] = {}
        for chave, req, nome, desc, unid, st, prazo, dt_envio in acoes_data:
            # Cada ação do mesmo requisito aponta para um item diferente
            # (varia o item real do catálogo, sempre pertencente ao requisito).
            itens_req = itens_por_cod.get(req, [])
            pos = item_por_requisito.get(req, 0)
            item_por_requisito[req] = pos + 1
            id_item = itens_req[pos % len(itens_req)][0] if itens_req else None
            acao = Acao(
                tenant_id=tenant.id,
                id_auditoria=auditoria_atual.id,
                id_requisito=req_id_por_cod[req],
                id_item=id_item,
                id_unidade=unid,
                nome=nome,
                descricao=desc,
                prazo=date.fromisoformat(prazo),
                data_envio=date.fromisoformat(dt_envio) if dt_envio else None,
                status=st,
                data_aprovacao=(
                    date.fromisoformat(dt_envio) if (dt_envio and st == "APROVADO") else None
                ),
                criado_por="u002",
            )
            db.add(acao)
            db.flush()
            acao_id_por_chave[chave] = acao.id_acao

            # Histórico da ação: criação e, quando aplicável, a evolução
            # do status até a situação atual.
            db.add(
                HistoricoAcao(
                    acao_id=acao.id_acao,
                    descricao_evento="Ação criada por Alana Abreu (Admin do Ente)",
                    usuario_id="u002",
                )
            )
            if dt_envio:
                db.add(
                    HistoricoAcao(
                        acao_id=acao.id_acao,
                        descricao_evento="Status alterado: PENDENTE → ENVIADO por Alana Abreu",
                        usuario_id="u002",
                    )
                )
            if st == "APROVADO":
                db.add(
                    HistoricoAcao(
                        acao_id=acao.id_acao,
                        descricao_evento="Status alterado: ENVIADO → APROVADO por Alana Abreu",
                        usuario_id="u002",
                    )
                )
            elif st == "DILIGÊNCIA":
                db.add(
                    HistoricoAcao(
                        acao_id=acao.id_acao,
                        descricao_evento="Status alterado: ENVIADO → DILIGÊNCIA por Alana Abreu",
                        usuario_id="u002",
                    )
                )
        db.flush()

        # ── DILIGÊNCIAS ───────────────────────────────────────────
        dils_data = DILIGENCIAS_DEMO
        for num, chave_acao, sit, crit, prazo, status_d in dils_data:
            db.add(
                Diligencia(
                    num=num,
                    acao_id=acao_id_por_chave[chave_acao],
                    situacao_detectada=sit,
                    criticidade=crit,
                    prazo_resposta=date.fromisoformat(prazo),
                    prazo_original=date.fromisoformat(prazo),
                    status=status_d,
                    emitido_por="u002",
                )
            )
        db.flush()

        # ── CERTIFICADO DO ENTE ───────────────────────────────────
        cert.status = "VENCIDA"
        cert.numero_certificado = "CERT-III-2024-0042"
        cert.data_certificacao = date(2024, 6, 1)
        cert.data_validade = date(2026, 6, 1)
        cert.entidade_certificadora = "IEPREV"

        # ── PROCESSO PRÓ-GESTÃO ───────────────────────────────────
        db.add(
            ProcessoProgestao(
                id="proc-fumpres-2026-001",
                tenant_id=tenant.id,
                nivel_pretendido="IV",
                tipo_processo="renovacao",
                entidade_certificadora="IEPREV",
                numero_protocolo="2026/0042-PG",
                data_adesao=date(2022, 3, 1),
                data_inicio_avaliacao=date(2026, 1, 15),
                data_prevista_auditoria=date(2026, 12, 10),
                status="em_andamento",
                dados_confirmados=False,
                criado_por="u001",
            )
        )

        # ── TAREFAS DEMO ──────────────────────────────────────────
        tarefas_demo = TAREFAS_DEMO
        for titulo, desc, uid, pri, prazo, st in tarefas_demo:
            db.add(
                Tarefa(
                    tenant_id=tenant.id,
                    titulo=titulo,
                    descricao=desc,
                    unidade_id=uid,
                    prioridade=pri,
                    prazo=date.fromisoformat(prazo),
                    status=st,
                    criado_por="u001",
                )
            )

        # ── EVIDÊNCIAS DEMO ───────────────────────────────────────
        # Cada evidência aponta para um requisito real do catálogo (por ID).
        evidencias_demo = EVIDENCIAS_DEMO
        for titulo, tipo, req, arq, tam in evidencias_demo:
            db.add(
                Evidencia(
                    tenant_id=tenant.id,
                    titulo=titulo,
                    tipo=tipo,
                    requisito_id=req_id_por_cod.get(req),
                    arquivo_nome=arq,
                    arquivo_tamanho=tam,
                    data_referencia=date(2026, 9, 1),
                    enviado_por="u002",
                )
            )

        db.commit()
        print("✅ Banco populado com sucesso!")
        print_credenciais()

    except Exception as exc:
        db.rollback()
        print(f"❌ Erro ao popular banco: {exc}")
        raise
    finally:
        db.close()


def print_credenciais() -> None:
    print("\n📋 Credenciais de acesso (senha: Demo@2026!):")
    print("   Admin Master   → admin@fumpres.ba.gov.br")
    print("   Admin do Ente  → auditor@fumpres.ba.gov.br")
    print("   Operador       → operador@fumpres.ba.gov.br")
    print("   Visualizador   → viewer@previc.gov.br")


# ══════════════════════════════════════════════════════════════════
# DADOS DEMO DE NEGÓCIO (aplicáveis a um banco já existente)
# ══════════════════════════════════════════════════════════════════

UNIDADES_DEMO = [
    ("un01", "DPR", "Diretoria de Previdência"),
    ("un02", "GEPRE", "Gerência de Previdência"),
    ("un03", "GECOP", "Gerência de Controle e Pagamento"),
    ("un04", "GEFIN", "Gerência Financeira"),
    ("un05", "UCGR", "Unidade de Controle e Gestão de Recursos"),
    ("un06", "GEINP", "Gerência de Informação e Publicidade"),
    ("un07", "OUVFUMPRES", "Ouvidoria FUMPRES"),
    ("un08", "GAB DPR", "Gabinete da Diretoria de Previdência"),
    ("un09", "ASSGER", "Assessoria de Gestão"),
    ("un10", "SEAPO", "Setor de Apoio ao Segurado"),
]

# (chave demo, requisito, nome, descrição, unidade, status, prazo, envio)
ACORES_DEMO = [
    ("AC-001", "3.1.1", "Mapear o fluxo de concessão de benefícios", "Mapeamento documentado com responsável, sistema e evidências", "un01", "PENDENTE", "2026-09-30", None),
    ("AC-002", "3.1.1", "Mapeamento da arrecadação", "Mapeamento da arrecadação mensal de contribuições e cobrança de débitos previdenciários", "un04", "PENDENTE", "2026-09-30", None),
    ("AC-003", "3.1.1", "Concluir mapeamento da arrecadação", "Fluxo de arrecadação mensal documentado e validado", "un05", "APROVADO", "2026-09-30", "2026-05-15"),
    ("AC-004", "3.1.1", "Mapeamento da arrecadação", "Mapeamento da arrecadação mensal de contribuições e cobrança de débitos previdenciários", "un02", "ENVIADO", "2026-09-30", "2026-06-10"),
    ("AC-005", "3.1.1", "Mapeamento do atendimento ao segurado", "Mapeamento do fluxo de atendimento presencial e remoto aos segurados", "un10", "APROVADO", "2026-09-30", "2026-06-02"),
    ("AC-006", "3.1.1", "Mapeamento das rotinas financeiras", "Mapeamento das rotinas financeiras e contabilidade do RPPS", "un04", "APROVADO", "2026-09-30", "2026-06-05"),
    ("AC-007", "3.1.1", "Mapeamento detalhado da concessão", "Mapeamento detalhado do fluxo de análise e concessão de benefícios", "un01", "PENDENTE", "2026-09-30", None),
    ("AC-008", "3.1.1", "Mapeamento dos processos da Ouvidoria", "Mapeamento dos processos da Ouvidoria e canais de manifestação", "un07", "PENDENTE", "2026-09-30", None),
    ("AC-011", "3.1.3", "Certificação do Diretor de Previdência", "Certificação profissional válida do Diretor de Previdência", "un01", "APROVADO", "2026-09-30", "2026-03-10"),
    ("AC-012", "3.1.3", "Certificação do Presidente do Conselho", "Certificação profissional do Presidente do Conselho Deliberativo", "un08", "APROVADO", "2026-09-30", "2026-03-12"),
    ("AC-013", "3.1.3", "Renovação da certificação da Gestora", "Certificação da Gestora de Previdência — vencida em mar/2026", "un08", "DILIGÊNCIA", "2026-06-23", "2026-03-01"),
    ("AC-021", "3.2.2", "Plano Estratégico do RPPS", "Planejamento Estratégico do RPPS aprovado pelo Conselho Deliberativo", "un01", "APROVADO", "2026-03-31", "2026-01-20"),
    ("AC-022", "3.2.2", "Plano de Ação Anual 2026", "Plano de Ação Anual 2026 com metas quantitativas e ata de aprovação do CD", "un04", "DILIGÊNCIA", "2026-03-15", "2026-03-01"),
    ("AC-023", "3.2.2", "Plano Plurianual do ente", "PPA do ente federativo vigente com ações do RPPS inseridas", "un01", "PENDENTE", "2026-09-30", None),
    ("AC-031", "3.2.8", "Publicar balanço anual no portal", "Balanço publicado com link permanente no portal da transparência", "un06", "APROVADO", "2026-06-30", "2026-01-20"),
    ("AC-032", "3.2.8", "Publicar relatório de gestão", "Relatório de Gestão anual publicado no portal de transparência", "un06", "APROVADO", "2026-06-30", "2026-01-25"),
    ("AC-033", "3.2.8", "Publicar demonstrações mensais", "Demonstrações financeiras mensais jan–jun/2026 publicadas no portal", "un06", "ENVIADO", "2026-07-17", "2026-07-18"),
    ("AC-041", "3.3.1", "Executar o plano de capacitação 2026", "Plano executado com lista de participantes e certificados", "un03", "APROVADO", "2026-09-30", "2026-03-15"),
    ("AC-042", "3.3.1", "Comprovação do Capacita FUMPRES 2026", "Comprovação de realização e certificados do Capacita FUMPRES 2026", "un03", "PENDENTE", "2026-11-30", None),
    ("AC-043", "3.3.1", "Certificados de capacitação da concessão", "Certificados dos servidores da área de concessão em capacitação técnica", "un01", "PENDENTE", "2026-11-30", None),
]

# (num, chave demo da ação, situação detectada, criticidade, prazo, status)
DILIGENCIAS_DEMO = [
    ("D-001", "AC-033", "Demonstrações financeiras mensais ausentes no portal. Publicar jan-jun/2026.", "alta", "2026-07-17", "retorno"),
    ("D-002", "AC-022", "Plano de Ação Anual 2026 enviado sem ata de aprovação do Conselho Deliberativo.", "critica", "2026-03-15", "vencida"),
    ("D-003", "AC-013", "Certificação da Gestora vencida em março/2026. Renovação obrigatória para manutenção do Nível IV.", "critica", "2026-06-23", "aberta"),
    ("D-004", "AC-004", "Mapeamento da compensação previdenciária incompleto — falta fluxograma assinado.", "media", "2026-07-31", "retorno"),
]

TAREFAS_DEMO = [
    ("Revisar Política de Controle Interno", "Atualizar conforme manual v4.1", "un01", "alta", "2026-11-15", "pendente"),
    ("Elaborar Ata da Reunião do CC", "Reunião de outubro/2026", "un02", "media", "2026-10-30", "em_andamento"),
    ("Enviar comprovante do Capacita 2026", "Certificados de participação", "un03", "alta", "2026-11-30", "pendente"),
    ("Atualizar mapa de riscos operacionais", "Ciclo anual de revisão", "un04", "critica", "2026-10-20", "em_andamento"),
    ("Publicar relatório no hotsite", "Relatório de conformidade Q3 2026", "un01", "baixa", "2026-11-05", "pendente"),
]

EVIDENCIAS_DEMO = [
    ("Política de Investimentos 2026", "politica", "3.2.1", "Politica_Invest_2026.pdf", 1240000),
    ("Ata CC Setembro 2026", "ata", "3.2.6", "Ata_CC_Set2026.pdf", 380000),
    ("Relatório de Compliance Q2 2026", "relatorio", "3.2.11", "Compliance_Q2_2026.pdf", 870000),
    ("Certificado Capacita RPPS 2025", "comprovante", "3.3.1", "Certif_Capacita2025.pdf", 215000),
    ("Mapa de Riscos 2026", "relatorio", "3.2.10", "MapaRiscos_2026.xlsx", 520000),
]


def popular_demo_negocio(db, tenant: Tenant) -> None:
    """Popula os dados de negócio demo (plano de ação, diligências, tarefas) em
    um banco que já tem a estrutura base e o catálogo.

    Não apaga nada: apenas cria o que ainda não existe. Ideal para popular
    um banco de desenvolvimento que já tem tenant, manual e itens.
    """
    manual = (
        db.query(Manual)
        .filter(Manual.versao_manual == "4.1")
        .order_by(Manual.id_manual)
        .first()
    )
    if manual is None:
        raise RuntimeError("Catálogo não encontrado — rode `python -m app.db.seed --demo`.")

    # Requisitos e itens do catálogo (por ID).
    req_id_por_cod: dict[str, int] = {
        r.cod_requisito: r.id_requisito
        for r in db.query(Requisito).filter(Requisito.id_manual == manual.id_manual).all()
    }
    itens_por_cod: dict[str, list[tuple[int, str]]] = {}
    for cod, rid in req_id_por_cod.items():
        itens = (
            db.query(Item)
            .filter(Item.id_requisito == rid)
            .order_by(Item.nivel, Item.id_item)
            .all()
        )
        if itens:
            itens_por_cod[cod] = [(i.id_item, i.nivel) for i in itens]

    # Certificado do ente (um por ente) e auditorias do manual.
    cert = (
        db.query(Certificacao)
        .filter(
            Certificacao.tenant_id == tenant.id,
            Certificacao.nome_certificacao == "Certificação Pró-Gestão RPPS",
        )
        .first()
    )
    if cert is None:
        cert = Certificacao(
            tenant_id=tenant.id,
            nome_certificacao="Certificação Pró-Gestão RPPS",
            status="PENDENTE",
        )
        db.add(cert)
        db.flush()

    auditorias_demo = [
        ("auditoria_inicial", "presencial", date(2024, 6, 1), "II", "aprovado"),
        ("supervisao_documental", "remota", date(2025, 6, 1), "III", "aprovado"),
        (
            "supervisao_presencial",
            "presencial",
            date(2026, 1, 15),
            "III",
            "aprovado_ressalvas",
        ),
        ("renovacao", "presencial", date(2026, 6, 1), "IV", "pendente"),
    ]
    auditoria_atual: Auditoria | None = None
    for tipo, modalidade, data_auditoria, recomendado, conclusao in auditorias_demo:
        aud = (
            db.query(Auditoria)
            .filter(
                Auditoria.tenant_id == tenant.id,
                Auditoria.id_certificacao == cert.id_certificacao,
                Auditoria.id_manual == manual.id_manual,
                Auditoria.tipo == tipo,
                Auditoria.data_auditoria == data_auditoria,
            )
            .first()
        )
        if aud is None:
            aud = Auditoria(
                tenant_id=tenant.id,
                id_certificacao=cert.id_certificacao,
                id_manual=manual.id_manual,
                tipo=tipo,
                modalidade=modalidade,
                data_auditoria=data_auditoria,
                duracao_horas=8.0,
                nivel_recomendado=recomendado,
                conclusao=conclusao,
                auditor_nome="Auditor IEPREV",
                criado_por="u001",
            )
            db.add(aud)
            db.flush()
        auditoria_atual = aud

    # Unidades demo (as que faltarem).
    for uid, sigla, nome in UNIDADES_DEMO:
        if db.get(Unidade, uid) is None:
            db.add(Unidade(id=uid, tenant_id=tenant.id, sigla=sigla, nome=nome, criado_por="u002"))
    db.flush()

    # Vínculos de perfil por unidade: o Operador e o Visualizador precisam de
    # uma unidade (é o que limita o escopo de ações/diligências deles).
    for uid, unid, pid in [("u003", "un04", "pf03"), ("u004", "un02", "pf04")]:
        vinculo = (
            db.query(UsuarioUnidadePerfil)
            .filter(
                UsuarioUnidadePerfil.usuario_id == uid,
                UsuarioUnidadePerfil.perfil_id == pid,
            )
            .first()
        )
        if vinculo is None:
            db.add(
                UsuarioUnidadePerfil(
                    usuario_id=uid, unidade_id=unid, perfil_id=pid, concedido_por="u001"
                )
            )
        elif not vinculo.unidade_id:
            vinculo.unidade_id = unid
    db.flush()

    # Vínculos requisito x unidade.
    req_unid_map = {
        "3.1.1": ["un01", "un04", "un05", "un02", "un10", "un07", "un08"],
        "3.1.3": ["un01", "un08"],
        "3.2.2": ["un01", "un04"],
        "3.2.8": ["un06"],
        "3.3.1": ["un03", "un01"],
    }
    for req_cod, uids in req_unid_map.items():
        rid = req_id_por_cod.get(req_cod)
        if rid is None:
            continue
        for uid in uids:
            existe = (
                db.query(RequisitoUnidade)
                .filter(
                    RequisitoUnidade.requisito_id == rid,
                    RequisitoUnidade.unidade_id == uid,
                )
                .first()
            )
            if not existe:
                db.add(RequisitoUnidade(requisito_id=rid, unidade_id=uid))
    db.flush()

    # Ações (uma linha por ação — o planejamento faz parte do registro).
    if db.query(Acao).filter(Acao.tenant_id == tenant.id).count() == 0:
        item_por_requisito: dict[str, int] = {}
        for _chave, req, nome, desc, unid, st, prazo, dt_envio in ACORES_DEMO:
            itens_req = itens_por_cod.get(req, [])
            if not itens_req:
                continue
            pos = item_por_requisito.get(req, 0)
            item_por_requisito[req] = pos + 1
            id_item = itens_req[pos % len(itens_req)][0]
            acao = Acao(
                tenant_id=tenant.id,
                id_auditoria=auditoria_atual.id,
                id_requisito=req_id_por_cod[req],
                id_item=id_item,
                id_unidade=unid,
                nome=nome,
                descricao=desc,
                prazo=date.fromisoformat(prazo),
                data_envio=date.fromisoformat(dt_envio) if dt_envio else None,
                status=st,
                data_aprovacao=(
                    date.fromisoformat(dt_envio) if (dt_envio and st == "APROVADO") else None
                ),
                criado_por="u002",
            )
            db.add(acao)
            db.flush()
            db.add(
                HistoricoAcao(
                    acao_id=acao.id_acao,
                    descricao_evento="Ação criada por João Silva (Admin do Ente)",
                    usuario_id="u002",
                )
            )
            if dt_envio:
                db.add(
                    HistoricoAcao(
                        acao_id=acao.id_acao,
                        descricao_evento="Status alterado: PENDENTE → ENVIADO por João Silva",
                        usuario_id="u002",
                    )
                )
            if st == "APROVADO":
                db.add(
                    HistoricoAcao(
                        acao_id=acao.id_acao,
                        descricao_evento="Status alterado: ENVIADO → APROVADO por João Silva",
                        usuario_id="u002",
                    )
                )
            elif st == "DILIGÊNCIA":
                db.add(
                    HistoricoAcao(
                        acao_id=acao.id_acao,
                        descricao_evento="Status alterado: ENVIADO → DILIGÊNCIA por João Silva",
                        usuario_id="u002",
                    )
                )
    db.flush()

    # Diligências (apontando por id_acao).
    if db.query(Diligencia).count() == 0:
        acoes = {a.id_acao: a for a in db.query(Acao).filter(Acao.tenant_id == tenant.id).all()}
        por_nome = {a.nome: a for a in acoes.values()}
        for num, chave_acao, sit, crit, prazo, status_d in DILIGENCIAS_DEMO:
            _, _, nome, _, _, _, _, _ = next(
                (a for a in ACORES_DEMO if a[0] == chave_acao),
                (None, None, None, None, None, None, None, None),
            )
            acao = por_nome.get(nome) if nome else None
            if acao is None:
                continue
            db.add(
                Diligencia(
                    num=num,
                    acao_id=acao.id_acao,
                    situacao_detectada=sit,
                    criticidade=crit,
                    prazo_resposta=date.fromisoformat(prazo),
                    prazo_original=date.fromisoformat(prazo),
                    status=status_d,
                    emitido_por="u002",
                )
            )
    db.flush()

    # Certificado do ente.
    cert.status = "VENCIDA"
    cert.numero_certificado = "CERT-III-2024-0042"
    cert.data_certificacao = date(2024, 6, 1)
    cert.data_validade = date(2026, 6, 1)
    cert.entidade_certificadora = "IEPREV"

    # Processo Pró-Gestão.
    if db.query(ProcessoProgestao).filter(ProcessoProgestao.tenant_id == tenant.id).count() == 0:
        db.add(
            ProcessoProgestao(
                id="proc-fumpres-2026-001",
                tenant_id=tenant.id,
                nivel_pretendido="IV",
                tipo_processo="renovacao",
                entidade_certificadora="IEPREV",
                numero_protocolo="2026/0042-PG",
                data_adesao=date(2022, 3, 1),
                data_inicio_avaliacao=date(2026, 1, 15),
                data_prevista_auditoria=date(2026, 12, 10),
                status="em_andamento",
                dados_confirmados=False,
                criado_por="u001",
            )
        )

    # Tarefas e evidências.
    if db.query(Tarefa).filter(Tarefa.tenant_id == tenant.id).count() == 0:
        for titulo, desc, uid, pri, prazo, st in TAREFAS_DEMO:
            db.add(
                Tarefa(
                    tenant_id=tenant.id,
                    titulo=titulo,
                    descricao=desc,
                    unidade_id=uid,
                    prioridade=pri,
                    prazo=date.fromisoformat(prazo),
                    status=st,
                    criado_por="u001",
                )
            )
    if db.query(Evidencia).filter(Evidencia.tenant_id == tenant.id).count() == 0:
        for titulo, tipo, req, arq, tam in EVIDENCIAS_DEMO:
            db.add(
                Evidencia(
                    tenant_id=tenant.id,
                    titulo=titulo,
                    tipo=tipo,
                    requisito_id=req_id_por_cod.get(req),
                    arquivo_nome=arq,
                    arquivo_tamanho=tam,
                    data_referencia=date(2026, 9, 1),
                    enviado_por="u002",
                )
            )

    db.commit()


if __name__ == "__main__":
    if "--demo-negocio" in sys.argv:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            tenant = db.query(Tenant).first()
            if tenant is None:
                print("Banco sem tenant — rode `python -m app.db.seed --demo` primeiro.")
            else:
                popular_demo_negocio(db, tenant)
                print("✅ Dados de negócio demo aplicados.")
        finally:
            db.close()
    else:
        seed(demo="--demo" in sys.argv)
