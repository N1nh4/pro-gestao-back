"""Popula o banco com os dados demo do FUMPRES.

Uso: python -m app.db.seed
"""

from datetime import date

from app.core.security import hash_senha
from app.db.base import Base, SessionLocal, engine

# Importa os modelos para registrar no metadata antes do create_all.
from app.models import (  # noqa: F401
    Acao,
    Certificacao,
    Diligencia,
    Evidencia,
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


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(Tenant).first():
            print("✓ Banco já populado. Pulando seed.")
            return

        print("⏳ Populando banco de dados...")

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
            ("u005", "005", "katiane.vieira", "katiane@fumpres.ba.gov.br", "Katiane Vieira"),
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

        # ── UNIDADES ──────────────────────────────────────────────
        unidades_data = [
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
        for uid, sigla, nome in unidades_data:
            db.add(Unidade(id=uid, tenant_id=tenant.id, sigla=sigla, nome=nome, criado_por="u002"))
        db.flush()

        # ── VÍNCULOS USUARIO-UNIDADE-PERFIL ───────────────────────
        vinculos = [
            ("u001", None, "pf01"),
            ("u002", None, "pf02"),
            ("u002", None, "pf05"),
            ("u003", "un04", "pf03"),
            ("u004", "un02", "pf04"),
            ("u005", "un03", "pf03"),
            ("u005", None, "pf05"),
        ]
        for uid, unid, pid in vinculos:
            db.add(
                UsuarioUnidadePerfil(
                    usuario_id=uid, unidade_id=unid, perfil_id=pid, concedido_por="u001"
                )
            )
        db.flush()

        # ── REQUISITOS (24 do Manual MPS/PREVIC v4.1) ─────────────
        reqs_data = [
            ("3.1.1", "CI", "Mapeamento das Atividades das Áreas", True),
            ("3.1.2", "CI", "Capacitação dos Responsáveis pelas Áreas", True),
            ("3.1.3", "CI", "Certificação dos Dirigentes e Membros dos Conselhos", True),
            ("3.1.4", "CI", "Plano de Capacitação dos Responsáveis", False),
            ("3.1.5", "CI", "Adesão ao CADPREV", True),
            ("3.1.6", "CI", "Implantação de Controles Internos", True),
            ("3.2.1", "GC", "Definição da Política de Investimentos", True),
            ("3.2.2", "GC", "Planejamento Estratégico", True),
            ("3.2.3", "GC", "Comitê de Investimentos", False),
            ("3.2.4", "GC", "Alienação de Bens e Direitos", False),
            ("3.2.5", "GC", "Instâncias de Deliberação", True),
            ("3.2.6", "GC", "Reuniões dos Conselhos", True),
            ("3.2.7", "GC", "Código de Ética e Conduta", False),
            ("3.2.8", "GC", "Transparência e Publicidade", True),
            ("3.2.9", "GC", "Canal de Denúncias", False),
            ("3.2.10", "GC", "Gestão de Riscos", False),
            ("3.2.11", "GC", "Relatório de Gestão", True),
            ("3.2.12", "GC", "Auditoria Interna", False),
            ("3.2.13", "GC", "Normas Internas", False),
            ("3.2.14", "GC", "Segregação de Funções", False),
            ("3.2.15", "GC", "Gestão de Pessoas", False),
            ("3.2.16", "GC", "Tecnologia da Informação", False),
            ("3.3.1", "EP", "Plano de Ação de Educação Previdenciária", True),
            ("3.3.2", "EP", "Programa de Educação Previdenciária", False),
        ]
        for cod, dim, titulo, ess in reqs_data:
            db.add(Requisito(cod=cod, dimensao=dim, titulo=titulo, essencial=ess))
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
                db.add(RequisitoUnidade(requisito_cod=req_cod, unidade_id=uid))
        db.flush()

        # ── AÇÕES (Plano de Ação) ─────────────────────────────────
        acoes_data = [
            ("AC-001", "3.1.1", "Benefícios", "Mapeamento documentado do processo de concessão, revisão e manutenção de aposentadorias e pensões", "un01", "PENDENTE", "2026-09-30", None),
            ("AC-002", "3.1.1", "Arrecadação", "Mapeamento da arrecadação mensal de contribuições e cobrança de débitos previdenciários", "un04", "PENDENTE", "2026-09-30", None),
            ("AC-003", "3.1.1", "Arrecadação", "Mapeamento da arrecadação mensal de contribuições e cobrança de débitos previdenciários", "un05", "APROVADO", "2026-09-30", "2026-05-15"),
            ("AC-004", "3.1.1", "Arrecadação", "Mapeamento da arrecadação mensal de contribuições e cobrança de débitos previdenciários", "un02", "ENVIADO", "2026-09-30", "2026-06-10"),
            ("AC-005", "3.1.1", "Atendimento ao Segurado", "Mapeamento do fluxo de atendimento presencial e remoto aos segurados", "un10", "APROVADO", "2026-09-30", "2026-06-02"),
            ("AC-006", "3.1.1", "Financeiro e Contábil", "Mapeamento das rotinas financeiras e contabilidade do RPPS", "un04", "APROVADO", "2026-09-30", "2026-06-05"),
            ("AC-007", "3.1.1", "Concessão e Revisão", "Mapeamento detalhado do fluxo de análise e concessão de benefícios", "un01", "PENDENTE", "2026-09-30", None),
            ("AC-008", "3.1.1", "Ouvidoria", "Mapeamento dos processos da Ouvidoria e canais de manifestação", "un07", "PENDENTE", "2026-09-30", None),
            ("AC-011", "3.1.3", "Diretor de Previdência", "Certificação profissional válida do Diretor de Previdência", "un01", "APROVADO", "2026-09-30", "2026-03-10"),
            ("AC-012", "3.1.3", "Conselho Deliberativo", "Certificação profissional do Presidente do Conselho Deliberativo", "un08", "APROVADO", "2026-09-30", "2026-03-12"),
            ("AC-013", "3.1.3", "Isabela Loureiro — Gestora", "Certificação da Gestora de Previdência — vencida em mar/2026", "un08", "DILIGÊNCIA", "2026-06-23", "2026-03-01"),
            ("AC-021", "3.2.2", "Plano Estratégico (5 anos)", "Planejamento Estratégico do RPPS aprovado pelo Conselho Deliberativo", "un01", "APROVADO", "2026-03-31", "2026-01-20"),
            ("AC-022", "3.2.2", "Plano de Ação Anual", "Plano de Ação Anual 2026 com metas quantitativas e ata de aprovação do CD", "un04", "DILIGÊNCIA", "2026-03-15", "2026-03-01"),
            ("AC-023", "3.2.2", "Plano Plurianual (PPA)", "PPA do ente federativo vigente com ações do RPPS inseridas", "un01", "PENDENTE", "2026-09-30", None),
            ("AC-031", "3.2.8", "Balanço Anual", "Balanço anual do RPPS publicado no portal de transparência", "un06", "APROVADO", "2026-06-30", "2026-01-20"),
            ("AC-032", "3.2.8", "Relatório de Gestão", "Relatório de Gestão anual publicado no portal de transparência", "un06", "APROVADO", "2026-06-30", "2026-01-25"),
            ("AC-033", "3.2.8", "Demonstrações Mensais", "Demonstrações financeiras mensais jan–jun/2026 publicadas no portal", "un06", "ENVIADO", "2026-07-17", "2026-07-18"),
            ("AC-041", "3.3.1", "Plano de Capacitação 2026", "Plano de Capacitação dos servidores do RPPS para 2026", "un03", "APROVADO", "2026-09-30", "2026-03-15"),
            ("AC-042", "3.3.1", "Capacita FUMPRES 2026", "Comprovação de realização e certificados do Capacita FUMPRES 2026", "un03", "PENDENTE", "2026-11-30", None),
            ("AC-043", "3.3.1", "Certificados Concessão", "Certificados dos servidores da área de concessão em capacitação técnica", "un01", "PENDENTE", "2026-11-30", None),
        ]
        for id_acao, req, item, desc, unid, st, prazo, dt_envio in acoes_data:
            db.add(
                Acao(
                    id_acao=id_acao,
                    tenant_id=tenant.id,
                    requisito_cod=req,
                    item=item,
                    descricao_acao=desc,
                    unidade_id=unid,
                    status=st,
                    prazo=date.fromisoformat(prazo),
                    dt_envio=date.fromisoformat(dt_envio) if dt_envio else None,
                    dt_aprovacao=date.fromisoformat(dt_envio) if (dt_envio and st == "APROVADO") else None,
                    criado_por="u002",
                )
            )
        db.flush()

        # ── DILIGÊNCIAS ───────────────────────────────────────────
        dils_data = [
            ("D-001", "AC-033", "Demonstrações financeiras mensais ausentes no portal. Publicar jan-jun/2026.", "alta", "2026-07-17", "retorno"),
            ("D-002", "AC-022", "Plano de Ação Anual 2026 enviado sem ata de aprovação do Conselho Deliberativo.", "critica", "2026-03-15", "vencida"),
            ("D-003", "AC-013", "Certificação da Gestora vencida em março/2026. Renovação obrigatória para manutenção do Nível IV.", "critica", "2026-06-23", "aberta"),
            ("D-004", "AC-004", "Mapeamento da compensação previdenciária incompleto — falta fluxograma assinado.", "media", "2026-07-31", "retorno"),
        ]
        for num, acao_id, sit, crit, prazo, status_d in dils_data:
            db.add(
                Diligencia(
                    num=num,
                    acao_id=acao_id,
                    situacao_detectada=sit,
                    criticidade=crit,
                    prazo_resposta=date.fromisoformat(prazo),
                    prazo_original=date.fromisoformat(prazo),
                    status=status_d,
                    emitido_por="u002",
                )
            )
        db.flush()

        # ── CERTIFICAÇÃO ──────────────────────────────────────────
        db.add(
            Certificacao(
                tenant_id=tenant.id,
                nivel="III",
                data_certificacao=date(2024, 6, 1),
                data_validade=date(2026, 6, 1),
                entidade_certificadora="IEPREV",
                status="expirada",
                numero_certificado="CERT-III-2024-0042",
                registrado_por="u002",
            )
        )

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
        tarefas_demo = [
            ("Revisar Política de Controle Interno", "Atualizar conforme manual v4.1", "un01", "alta", "2026-11-15", "pendente"),
            ("Elaborar Ata da Reunião do CC", "Reunião de outubro/2026", "un02", "media", "2026-10-30", "em_andamento"),
            ("Enviar comprovante do Capacita 2026", "Certificados de participação", "un03", "alta", "2026-11-30", "pendente"),
            ("Atualizar mapa de riscos operacionais", "Ciclo anual de revisão", "un04", "critica", "2026-10-20", "em_andamento"),
            ("Publicar relatório no hotsite", "Relatório de conformidade Q3 2026", "un01", "baixa", "2026-11-05", "pendente"),
        ]
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
        evidencias_demo = [
            ("Política de Investimentos 2026", "politica", "1.1", "Politica_Invest_2026.pdf", 1240000),
            ("Ata CC Setembro 2026", "ata", "2.1", "Ata_CC_Set2026.pdf", 380000),
            ("Relatório de Compliance Q2 2026", "relatorio", "1.3", "Compliance_Q2_2026.pdf", 870000),
            ("Certificado Capacita RPPS 2025", "comprovante", "3.1", "Certif_Capacita2025.pdf", 215000),
            ("Mapa de Riscos 2026", "relatorio", "1.4", "MapaRiscos_2026.xlsx", 520000),
        ]
        for titulo, tipo, req, arq, tam in evidencias_demo:
            db.add(
                Evidencia(
                    tenant_id=tenant.id,
                    titulo=titulo,
                    tipo=tipo,
                    requisito_cod=req,
                    arquivo_nome=arq,
                    arquivo_tamanho=tam,
                    data_referencia=date(2026, 9, 1),
                    enviado_por="u002",
                )
            )

        db.commit()
        print("✅ Banco populado com sucesso!")
        print("\n📋 Credenciais de acesso (senha: Demo@2026!):")
        print("   Admin Master   → admin@fumpres.ba.gov.br")
        print("   Admin do Ente  → auditor@fumpres.ba.gov.br")
        print("   Operador       → operador@fumpres.ba.gov.br")
        print("   Visualizador   → viewer@previc.gov.br")
        print("   Katiane Vieira → katiane@fumpres.ba.gov.br")

    except Exception as exc:
        db.rollback()
        print(f"❌ Erro ao popular banco: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
