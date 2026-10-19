"""Certificações e auditorias."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_usuario_atual
from app.db import get_db
from app.models import Auditoria, Certificacao, Usuario
from app.schemas import (
    AuditoriaCreate,
    AuditoriaOut,
    CertificacaoCreate,
    CertificacaoOut,
)

router = APIRouter(tags=["Certificações"])


@router.get("/api/certificacoes", response_model=list[CertificacaoOut])
def listar_certificacoes(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    return (
        db.query(Certificacao)
        .filter(Certificacao.tenant_id == usuario.tenant_id)
        .order_by(Certificacao.data_certificacao.desc())
        .all()
    )


@router.post("/api/certificacoes", response_model=CertificacaoOut)
def criar_certificacao(
    payload: CertificacaoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    cert = Certificacao(
        tenant_id=usuario.tenant_id,
        registrado_por=usuario.id,
        **payload.model_dump(),
    )
    db.add(cert)
    db.commit()
    db.refresh(cert)
    return cert


@router.get("/api/auditorias", response_model=list[AuditoriaOut])
def listar_auditorias(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    return (
        db.query(Auditoria)
        .filter(Auditoria.tenant_id == usuario.tenant_id)
        .order_by(Auditoria.data_auditoria.desc())
        .all()
    )


@router.post("/api/auditorias", response_model=AuditoriaOut)
def criar_auditoria(
    payload: AuditoriaCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    aud = Auditoria(
        tenant_id=usuario.tenant_id,
        criado_por=usuario.id,
        **payload.model_dump(),
    )
    db.add(aud)
    db.commit()
    db.refresh(aud)
    return aud
