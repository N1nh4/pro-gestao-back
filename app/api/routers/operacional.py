"""Operacional: tarefas, evidências (GED) e processos/onboarding."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_usuario_atual
from app.db import get_db
from app.models import (
    Evidencia,
    ProcessoProgestao,
    Requisito,
    Tarefa,
    Tenant,
    Usuario,
)
from app.schemas import (
    EvidenciaCreate,
    ProcessoCreate,
    ProcessoOut,
    ProcessoStatusUpdate,
    TarefaCreate,
    TarefaStatusUpdate,
)

router = APIRouter(tags=["Operacional"])


# ── TAREFAS ──────────────────────────────────────────────────────
@router.get("/api/tarefas")
def listar_tarefas(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    rows = (
        db.query(Tarefa)
        .filter(Tarefa.tenant_id == usuario.tenant_id)
        .order_by(Tarefa.prazo.asc())
        .all()
    )
    return [
        {
            "id": r.id,
            "titulo": r.titulo,
            "descricao": r.descricao,
            "prioridade": r.prioridade,
            "status": r.status,
            "prazo": str(r.prazo) if r.prazo else None,
            "acao_id": r.acao_id,
            "unidade_id": r.unidade_id,
        }
        for r in rows
    ]


@router.post("/api/tarefas")
def criar_tarefa(
    payload: TarefaCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    tarefa = Tarefa(
        tenant_id=usuario.tenant_id,
        criado_por=usuario.id,
        **payload.model_dump(),
    )
    db.add(tarefa)
    db.commit()
    db.refresh(tarefa)
    return {"id": tarefa.id, "titulo": tarefa.titulo}


@router.patch("/api/tarefas/{tid}/status")
def atualizar_status_tarefa(
    tid: str,
    payload: TarefaStatusUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    tarefa = (
        db.query(Tarefa)
        .filter(Tarefa.id == tid, Tarefa.tenant_id == usuario.tenant_id)
        .first()
    )
    if not tarefa:
        raise HTTPException(404, "Tarefa não encontrada")
    tarefa.status = payload.status
    if tarefa.status == "concluida":
        tarefa.concluida_em = datetime.utcnow()
    db.commit()
    return {"id": tarefa.id, "status": tarefa.status}


# ── GED — EVIDÊNCIAS ─────────────────────────────────────────────
@router.get("/api/evidencias")
def listar_evidencias(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    rows = (
        db.query(Evidencia)
        .options(joinedload(Evidencia.requisito))
        .filter(Evidencia.tenant_id == usuario.tenant_id)
        .order_by(Evidencia.criado_em.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "titulo": r.titulo,
            "tipo": r.tipo,
            "id_requisito": r.requisito_id,
            "requisito_cod": r.requisito.cod_requisito if r.requisito else None,
            "acao_id": r.acao_id,
            "arquivo_nome": r.arquivo_nome,
            "arquivo_tamanho": r.arquivo_tamanho,
            "data_referencia": str(r.data_referencia) if r.data_referencia else None,
            "validade": str(r.validade) if r.validade else None,
            "observacoes": r.observacoes,
        }
        for r in rows
    ]


@router.post("/api/evidencias")
def enviar_evidencia(
    payload: EvidenciaCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    dados = payload.model_dump()
    cod_legado = dados.pop("requisito_cod", None)
    requisito_id = dados.pop("id_requisito", None)

    # Resolve o requisito por ID (preferencial) ou pelo código legado.
    if requisito_id is None and cod_legado:
        req = db.query(Requisito).filter(Requisito.cod_requisito == cod_legado).first()
        requisito_id = req.id_requisito if req else None
    dados["requisito_id"] = requisito_id

    evidencia = Evidencia(
        tenant_id=usuario.tenant_id,
        enviado_por=usuario.id,
        **dados,
    )
    db.add(evidencia)
    db.commit()
    db.refresh(evidencia)
    return {"id": evidencia.id, "titulo": evidencia.titulo}


# ── ONBOARDING ───────────────────────────────────────────────────
@router.get("/api/onboarding/status")
def onboarding_status(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    tenant = db.query(Tenant).filter(Tenant.id == usuario.tenant_id).first()
    if not tenant:
        raise HTTPException(404, "Ente não encontrado")

    processo_ativo = (
        db.query(ProcessoProgestao)
        .filter(
            ProcessoProgestao.tenant_id == usuario.tenant_id,
            ProcessoProgestao.status == "em_andamento",
        )
        .first()
    )
    primeiro_processo = (
        db.query(ProcessoProgestao)
        .filter(ProcessoProgestao.tenant_id == usuario.tenant_id)
        .order_by(ProcessoProgestao.criado_em.asc())
        .first()
    )
    dados_confirmados = primeiro_processo.dados_confirmados if primeiro_processo else False

    return {
        "ente": {
            "id": tenant.id,
            "nome": tenant.nome_ente,
            "cnpj_ente": tenant.cnpj_ente,
            "uf": tenant.uf,
            "tipo_ente": tenant.tipo_ente,
            "unidade_gestora": tenant.nome_ug,
            "cnpj_ug": tenant.cnpj_ug,
            "email": tenant.email_contato,
            "telefone": tenant.telefone_contato,
            "num_segurados": tenant.num_segurados,
            "endereco": None,
            "representante_nome": None,
            "representante_cargo": None,
            "representante_email": None,
        },
        "dados_confirmados": dados_confirmados,
        "tem_processo_ativo": processo_ativo is not None,
        "processo_ativo": (
            {
                "id": processo_ativo.id,
                "nivel_pretendido": processo_ativo.nivel_pretendido,
                "status": processo_ativo.status,
            }
            if processo_ativo
            else None
        ),
    }


@router.post("/api/onboarding/confirmar-dados")
def confirmar_dados(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    processo = (
        db.query(ProcessoProgestao)
        .filter(ProcessoProgestao.tenant_id == usuario.tenant_id)
        .order_by(ProcessoProgestao.criado_em.asc())
        .first()
    )
    if processo:
        processo.dados_confirmados = True
        processo.dados_confirmados_em = datetime.utcnow()
        processo.dados_confirmados_por = usuario.id
        db.commit()
    return {"mensagem": "Dados confirmados com sucesso."}


# ── PROCESSOS PRÓ-GESTÃO ─────────────────────────────────────────
@router.get("/api/processos", response_model=list[ProcessoOut])
def listar_processos(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    return (
        db.query(ProcessoProgestao)
        .filter(ProcessoProgestao.tenant_id == usuario.tenant_id)
        .order_by(ProcessoProgestao.criado_em.desc())
        .all()
    )


@router.post("/api/processos", response_model=ProcessoOut)
def criar_processo(
    payload: ProcessoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    ativo = (
        db.query(ProcessoProgestao)
        .filter(
            ProcessoProgestao.tenant_id == usuario.tenant_id,
            ProcessoProgestao.status == "em_andamento",
        )
        .first()
    )
    if ativo:
        raise HTTPException(409, "Já existe um processo em andamento para este ente.")

    proc = ProcessoProgestao(
        tenant_id=usuario.tenant_id,
        dados_confirmados=False,
        criado_por=usuario.id,
        **payload.model_dump(),
    )
    db.add(proc)
    db.commit()
    db.refresh(proc)
    return proc


@router.put("/api/processos/{pid}/status")
def atualizar_processo(
    pid: str,
    payload: ProcessoStatusUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    proc = (
        db.query(ProcessoProgestao)
        .filter(
            ProcessoProgestao.id == pid,
            ProcessoProgestao.tenant_id == usuario.tenant_id,
        )
        .first()
    )
    if not proc:
        raise HTTPException(404, "Processo não encontrado")

    if payload.status:
        proc.status = payload.status
    if payload.nivel_certificado:
        proc.nivel_certificado = payload.nivel_certificado
    if payload.observacoes:
        proc.observacoes = payload.observacoes
    proc.atualizado_em = datetime.utcnow()
    db.commit()
    return {"id": proc.id, "status": proc.status}
