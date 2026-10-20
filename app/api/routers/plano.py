"""Plano de Ação: CRUD de ações e mudança de status."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_usuario_atual, nomes_perfis
from app.db import get_db
from app.models import (
    Acao,
    Diligencia,
    HistoricoAcao,
    Requisito,
    Unidade,
    Usuario,
    UsuarioUnidadePerfil,
)
from app.schemas import AcaoCreate, AcaoStatusUpdate

router = APIRouter(prefix="/api/acoes", tags=["Plano de Ação"])

_PERFIS_ADMIN = {"Admin do Ente", "Admin Master"}
_PREFIXO_DIMENSAO = {"CI": "3.1", "GC": "3.2", "EP": "3.3"}


def _resolver_requisito(db: Session, *, id_requisito: int | None, cod: str | None) -> Requisito:
    """Resolve o requisito por ID (preferencial) ou por código legado."""
    if id_requisito is not None:
        req = db.get(Requisito, id_requisito)
        if not req:
            raise HTTPException(status_code=422, detail="Requisito não encontrado")
        return req
    if cod:
        req = (
            db.query(Requisito).filter(Requisito.cod_requisito == cod).first()
        )
        if not req:
            raise HTTPException(status_code=422, detail="Requisito não encontrado")
        return req
    raise HTTPException(status_code=422, detail="Informe id_requisito ou requisito_cod")


@router.get("")
def listar_acoes(
    status: str | None = Query(None),
    dimensao: str | None = Query(None),
    unidade_id: str | None = Query(None),
    requisito: str | None = Query(None),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    q = db.query(Acao).filter(Acao.tenant_id == usuario.tenant_id)

    perfis = nomes_perfis(db, usuario)
    if "Operador" in perfis and not perfis.intersection(_PERFIS_ADMIN):
        unidades_usuario = [
            v.unidade_id
            for v in db.query(UsuarioUnidadePerfil)
            .filter(UsuarioUnidadePerfil.usuario_id == usuario.id)
            .all()
            if v.unidade_id
        ]
        if unidades_usuario:
            q = q.filter(Acao.unidade_id.in_(unidades_usuario))

    if status:
        q = q.filter(Acao.status == status)
    if unidade_id:
        q = q.filter(Acao.unidade_id == unidade_id)
    if requisito:
        q = q.join(Requisito, Requisito.id_requisito == Acao.requisito_id).filter(
            Requisito.cod_requisito == requisito
        )
    if dimensao:
        prefix = _PREFIXO_DIMENSAO.get(dimensao, "")
        if prefix:
            q = q.join(Requisito, Requisito.id_requisito == Acao.requisito_id).filter(
                Requisito.cod_requisito.like(f"{prefix}%")
            )

    acoes = (
        q.options(joinedload(Acao.requisito))
        .order_by(Acao.requisito_id, Acao.id_acao)
        .all()
    )

    result = []
    for a in acoes:
        unidade = db.query(Unidade).filter(Unidade.id == a.unidade_id).first()
        hist = (
            db.query(HistoricoAcao)
            .filter(HistoricoAcao.acao_id == a.id_acao)
            .order_by(HistoricoAcao.data_evento.desc())
            .all()
        )
        dilig_count = (
            db.query(func.count(Diligencia.id))
            .filter(Diligencia.acao_id == a.id_acao)
            .scalar()
        )

        result.append(
            {
                "id_acao": a.id_acao,
                "id_requisito": a.requisito_id,
                "requisito_cod": a.requisito.cod_requisito if a.requisito else "",
                "item": a.item,
                "descricao_acao": a.descricao_acao,
                "unidade_id": a.unidade_id,
                "unidade_sigla": unidade.sigla if unidade else "",
                "unidade_nome": unidade.nome if unidade else "",
                "status": a.status,
                "prazo": a.prazo.isoformat() if a.prazo else None,
                "dt_envio": a.dt_envio.isoformat() if a.dt_envio else None,
                "dt_aprovacao": a.dt_aprovacao.isoformat() if a.dt_aprovacao else None,
                "criado_em": a.criado_em.isoformat() if a.criado_em else None,
                "diligencias_count": dilig_count,
                "historico": [
                    {"dt": h.data_evento.strftime("%d/%m"), "ev": h.descricao_evento}
                    for h in hist
                ],
            }
        )
    return result


@router.post("")
def criar_acao(
    req: AcaoCreate,
    db: Session = Depends(get_db),
    atual: Usuario = Depends(get_usuario_atual),
):
    """Cria uma ação por unidade informada (multi-setor)."""
    alvos = req.unidade_ids or ([req.unidade_id] if req.unidade_id else [])
    if not alvos:
        raise HTTPException(status_code=422, detail="Informe ao menos uma unidade")

    requisito = _resolver_requisito(
        db, id_requisito=req.id_requisito, cod=req.requisito_cod
    )

    criadas = []
    total = (
        db.query(func.count(Acao.id_acao))
        .filter(Acao.tenant_id == atual.tenant_id)
        .scalar()
        or 0
    )
    for i, uid in enumerate(alvos, start=1):
        seq = total + i
        id_acao = f"AC-{str(seq).zfill(3)}"
        while db.query(Acao).filter(Acao.id_acao == id_acao).first():
            seq += 1
            id_acao = f"AC-{str(seq).zfill(3)}"

        db.add(
            Acao(
                id_acao=id_acao,
                tenant_id=atual.tenant_id,
                requisito_id=requisito.id_requisito,
                item=req.item,
                descricao_acao=req.descricao_acao,
                unidade_id=uid,
                status="PENDENTE",
                prazo=req.prazo,
                criado_por=atual.id,
            )
        )
        db.flush()
        db.add(
            HistoricoAcao(
                acao_id=id_acao,
                descricao_evento=f"Ação criada por {atual.nome_completo}",
                usuario_id=atual.id,
            )
        )
        criadas.append(id_acao)

    db.commit()
    return {"criadas": criadas, "total": len(criadas)}


@router.patch("/{id_acao}/status")
def atualizar_status(
    id_acao: str,
    req: AcaoStatusUpdate,
    db: Session = Depends(get_db),
    atual: Usuario = Depends(get_usuario_atual),
):
    acao = (
        db.query(Acao)
        .filter(Acao.id_acao == id_acao, Acao.tenant_id == atual.tenant_id)
        .first()
    )
    if not acao:
        raise HTTPException(status_code=404, detail="Ação não encontrada")

    status_anterior = acao.status
    acao.status = req.status
    if req.status == "ENVIADO":
        acao.dt_envio = date.today()
    elif req.status == "APROVADO":
        acao.dt_aprovacao = date.today()

    db.add(
        HistoricoAcao(
            acao_id=id_acao,
            descricao_evento=(
                f"Status alterado: {status_anterior} → {req.status} "
                f"por {atual.nome_completo}"
            ),
            usuario_id=atual.id,
        )
    )
    db.commit()
    return {"id_acao": id_acao, "status": req.status}
