"""Certificações (tabela única `certificacao`) e auditorias.

Cada linha é a certificação do ente em um nível de um manual, com status,
número do certificado, datas e entidade certificadora.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_usuario_atual, requer_perfil
from app.db import get_db
from app.models import Auditoria, Certificacao, Manual, Nivel, Usuario
from app.schemas import (
    AuditoriaCreate,
    AuditoriaOut,
    CertificacaoCreate,
    CertificacaoOut,
    CertificacaoUpdate,
)

router = APIRouter(tags=["Certificações"])

_admin = requer_perfil("Admin Master", "Admin do Ente")

_STATUS_VALIDOS = {"PENDENTE", "VIGENTE", "VENCIDA", "REVOGADA"}


def _montar_out(c: Certificacao) -> CertificacaoOut:
    return CertificacaoOut(
        id_certificacao=c.id_certificacao,
        id_manual=c.id_manual,
        id_nivel=c.id_nivel,
        nome_certificacao=c.nome_certificacao,
        status=c.status,
        numero_certificado=c.numero_certificado,
        data_certificacao=c.data_certificacao,
        data_validade=c.data_validade,
        entidade_certificadora=c.entidade_certificadora,
        criado_em=c.criado_em,
        atualizado_em=c.atualizado_em,
        nome_nivel=c.nivel.nome_nivel if c.nivel else "",
        nome_manual=c.manual.nome_manual if c.manual else "",
        versao_manual=c.manual.versao_manual if c.manual else "",
    )


@router.get("/api/certificacoes", response_model=list[CertificacaoOut])
def listar_certificacoes(
    id_manual: int | None = Query(None),
    id_nivel: int | None = Query(None),
    status: str | None = Query(None),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    q = db.query(Certificacao).filter(Certificacao.tenant_id == usuario.tenant_id)
    if id_manual is not None:
        q = q.filter(Certificacao.id_manual == id_manual)
    if id_nivel is not None:
        q = q.filter(Certificacao.id_nivel == id_nivel)
    if status:
        q = q.filter(Certificacao.status == status)

    certs = (
        q.options(
            joinedload(Certificacao.nivel),
            joinedload(Certificacao.manual),
        )
        .order_by(Certificacao.id_manual, Certificacao.id_nivel)
        .all()
    )
    return [_montar_out(c) for c in certs]


@router.post("/api/certificacoes", response_model=CertificacaoOut, status_code=201)
def criar_certificacao(
    payload: CertificacaoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(_admin),
):
    if payload.status not in _STATUS_VALIDOS:
        raise HTTPException(
            status_code=422,
            detail="Status deve ser PENDENTE, VIGENTE, VENCIDA ou REVOGADA",
        )
    if not db.get(Manual, payload.id_manual):
        raise HTTPException(status_code=422, detail="Manual não encontrado")
    if not db.get(Nivel, payload.id_nivel):
        raise HTTPException(status_code=422, detail="Nível não encontrado")

    conflito = (
        db.query(Certificacao)
        .filter(
            Certificacao.tenant_id == usuario.tenant_id,
            Certificacao.id_manual == payload.id_manual,
            Certificacao.id_nivel == payload.id_nivel,
        )
        .first()
    )
    if conflito:
        raise HTTPException(
            status_code=409,
            detail="Este ente já possui certificação para o nível deste manual",
        )

    cert = Certificacao(
        tenant_id=usuario.tenant_id,
        **payload.model_dump(),
    )
    db.add(cert)
    db.commit()
    db.refresh(cert)
    return _montar_out(cert)


@router.put("/api/certificacoes/{id_certificacao}", response_model=CertificacaoOut)
def atualizar_certificacao(
    id_certificacao: int,
    payload: CertificacaoUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    cert = (
        db.query(Certificacao)
        .filter(
            Certificacao.id_certificacao == id_certificacao,
            Certificacao.tenant_id == usuario.tenant_id,
        )
        .first()
    )
    if not cert:
        raise HTTPException(status_code=404, detail="Certificação não encontrada")

    dados = payload.model_dump(exclude_unset=True)
    if "status" in dados and dados["status"] not in _STATUS_VALIDOS:
        raise HTTPException(
            status_code=422,
            detail="Status deve ser PENDENTE, VIGENTE, VENCIDA ou REVOGADA",
        )
    if "id_nivel" in dados and not db.get(Nivel, dados["id_nivel"]):
        raise HTTPException(status_code=422, detail="Nível não encontrado")

    id_nivel = dados.get("id_nivel", cert.id_nivel)
    if id_nivel != cert.id_nivel:
        conflito = (
            db.query(Certificacao)
            .filter(
                Certificacao.tenant_id == usuario.tenant_id,
                Certificacao.id_manual == cert.id_manual,
                Certificacao.id_nivel == id_nivel,
                Certificacao.id_certificacao != cert.id_certificacao,
            )
            .first()
        )
        if conflito:
            raise HTTPException(
                status_code=409,
                detail="Este ente já possui certificação para o nível deste manual",
            )

    for campo, valor in dados.items():
        setattr(cert, campo, valor)
    db.commit()
    db.refresh(cert)
    return _montar_out(cert)


@router.delete("/api/certificacoes/{id_certificacao}", status_code=204)
def remover_certificacao(
    id_certificacao: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    cert = (
        db.query(Certificacao)
        .filter(
            Certificacao.id_certificacao == id_certificacao,
            Certificacao.tenant_id == usuario.tenant_id,
        )
        .first()
    )
    if not cert:
        raise HTTPException(status_code=404, detail="Certificação não encontrada")
    if cert.acoes:
        raise HTTPException(
            status_code=409,
            detail="A certificação possui ações vinculadas",
        )
    db.delete(cert)
    db.commit()


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
