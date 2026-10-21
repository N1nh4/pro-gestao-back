"""Diligências: emissão, retorno e aprovação."""

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_usuario_atual, requer_perfil
from app.db import get_db
from app.models import (
    Acao,
    Diligencia,
    HistoricoAcao,
    HistoricoDiligencia,
    Usuario,
)
from app.schemas import DiligenciaCreate, DiligenciaRetorno

router = APIRouter(prefix="/api/diligencias", tags=["Diligências"])
_admin = requer_perfil("Admin Master", "Admin do Ente")


@router.get("")
def listar_diligencias(
    status: str | None = Query(None),
    acao_id: int | None = Query(None),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    q = (
        db.query(Diligencia)
        .join(Acao)
        .filter(Acao.tenant_id == usuario.tenant_id)
    )
    if status:
        q = q.filter(Diligencia.status == status)
    if acao_id:
        q = q.filter(Diligencia.acao_id == acao_id)

    diligencias = q.order_by(Diligencia.emitido_em.desc()).all()
    return [
        {
            "id": d.id,
            "num": d.num,
            "acao_id": d.acao_id,
            "situacao_detectada": d.situacao_detectada,
            "criticidade": d.criticidade,
            "prazo_resposta": d.prazo_resposta.isoformat() if d.prazo_resposta else None,
            "status": d.status,
            "emitido_em": d.emitido_em.isoformat() if d.emitido_em else None,
            "retorno_texto": d.retorno_texto,
            "retorno_em": d.retorno_em.isoformat() if d.retorno_em else None,
        }
        for d in diligencias
    ]


@router.post("")
def criar_diligencia(
    req: DiligenciaCreate,
    db: Session = Depends(get_db),
    atual: Usuario = Depends(_admin),
):
    acao = (
        db.query(Acao)
        .filter(Acao.id_acao == req.acao_id, Acao.tenant_id == atual.tenant_id)
        .first()
    )
    if not acao:
        raise HTTPException(status_code=404, detail="Ação não encontrada")
    if acao.status != "ENVIADO":
        raise HTTPException(
            status_code=409,
            detail="A ação precisa estar enviada para receber uma diligência",
        )
    if req.criticidade not in {"critica", "alta", "media", "baixa"}:
        raise HTTPException(status_code=422, detail="Criticidade inválida")

    total = (
        db.query(func.count(Diligencia.id))
        .join(Acao)
        .filter(Acao.tenant_id == atual.tenant_id)
        .scalar()
        or 0
    )
    num = f"D-{str(total + 1).zfill(3)}"

    nova = Diligencia(
        num=num,
        acao_id=req.acao_id,
        situacao_detectada=req.situacao_detectada,
        criticidade=req.criticidade,
        prazo_resposta=req.prazo_resposta,
        prazo_original=req.prazo_resposta,
        status="aberta",
        emitido_por=atual.id,
    )
    db.add(nova)
    db.flush()

    acao.status = "DILIGÊNCIA"
    db.add(
        HistoricoAcao(
            acao_id=req.acao_id,
            descricao_evento=f"{num} emitida: {req.situacao_detectada[:60]}",
            usuario_id=atual.id,
        )
    )
    db.add(
        HistoricoDiligencia(
            diligencia_id=nova.id,
            descricao_evento=f"{num} emitida por {atual.nome_completo}",
            usuario_id=atual.id,
        )
    )
    db.commit()
    return {"id": nova.id, "num": num}


@router.patch("/{dil_id}/retorno")
def enviar_retorno(
    dil_id: str,
    req: DiligenciaRetorno,
    db: Session = Depends(get_db),
    atual: Usuario = Depends(get_usuario_atual),
):
    dil = db.query(Diligencia).filter(Diligencia.id == dil_id).first()
    if not dil:
        raise HTTPException(status_code=404, detail="Diligência não encontrada")

    dil.retorno_texto = req.retorno_texto
    dil.retorno_em = datetime.utcnow()
    dil.status = "retorno"

    db.add(
        HistoricoDiligencia(
            diligencia_id=dil_id,
            descricao_evento=f"Retorno enviado por {atual.nome_completo}: {req.retorno_texto[:60]}",
            usuario_id=atual.id,
        )
    )
    db.commit()
    return {"status": "retorno"}


@router.patch("/{dil_id}/aprovar")
def aprovar_diligencia(
    dil_id: str,
    db: Session = Depends(get_db),
    atual: Usuario = Depends(_admin),
):
    dil = (
        db.query(Diligencia)
        .join(Acao)
        .filter(Diligencia.id == dil_id, Acao.tenant_id == atual.tenant_id)
        .first()
    )
    if not dil:
        raise HTTPException(status_code=404, detail="Diligência não encontrada")

    dil.status = "aprovada"
    acao = db.query(Acao).filter(Acao.id_acao == dil.acao_id).first()
    if acao:
        acao.status = "APROVADO"
        acao.data_aprovacao = date.today()
        db.add(
            HistoricoAcao(
                acao_id=acao.id_acao,
                descricao_evento=f"✓ Aprovado — retorno da {dil.num} aceito por {atual.nome_completo}",
                usuario_id=atual.id,
            )
        )

    db.add(
        HistoricoDiligencia(
            diligencia_id=dil_id,
            descricao_evento=f"Retorno aprovado por {atual.nome_completo} — diligência concluída",
            usuario_id=atual.id,
        )
    )
    db.commit()
    return {"status": "aprovada", "acao_status": "APROVADO"}
