"""Certificações do ente e suas auditorias.

Hierarquia: `certificacao` 1---N `auditoria` 1---N `acao`.

- A certificação guarda o certificado (status, número, datas, entidade).
- Cada auditoria pertence à certificação e seleciona um manual; é nela
  que o plano de ação (as ações) é montado.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_usuario_atual, requer_perfil
from app.db import get_db
from app.models import Acao, Auditoria, Certificacao, Manual, Usuario
from app.schemas import (
    AuditoriaCreate,
    AuditoriaOut,
    AuditoriaUpdate,
    CertificacaoCreate,
    CertificacaoOut,
    CertificacaoUpdate,
)

router = APIRouter(tags=["Certificações"])

_admin = requer_perfil("Admin Master", "Admin do Ente")

_STATUS_CERTIFICACAO = {"PENDENTE", "VIGENTE", "VENCIDA", "REVOGADA"}


# ── Contagens agregadas (uma consulta por nível de agregação) ────────────────


def _contagens(db: Session, tenant_id: str) -> tuple[dict[int, int], dict[int, int]]:
    auditorias = dict(
        db.query(Auditoria.id_certificacao, func.count(Auditoria.id))
        .filter(Auditoria.tenant_id == tenant_id)
        .group_by(Auditoria.id_certificacao)
        .all()
    )
    acoes = dict(
        db.query(Auditoria.id_certificacao, func.count(Acao.id_acao))
        .join(Acao, Acao.id_auditoria == Auditoria.id)
        .filter(Auditoria.tenant_id == tenant_id)
        .group_by(Auditoria.id_certificacao)
        .all()
    )
    return auditorias, acoes


def _montar_certificacao(
    c: Certificacao,
    auditorias: int = 0,
    acoes: int = 0,
) -> CertificacaoOut:
    return CertificacaoOut(
        id_certificacao=c.id_certificacao,
        nome_certificacao=c.nome_certificacao,
        status=c.status,
        numero_certificado=c.numero_certificado,
        data_certificacao=c.data_certificacao,
        data_validade=c.data_validade,
        entidade_certificadora=c.entidade_certificadora,
        criado_em=c.criado_em,
        atualizado_em=c.atualizado_em,
        auditorias_count=auditorias,
        acoes_count=acoes,
    )


def _buscar_certificacao(db: Session, id_certificacao: int, tenant_id: str) -> Certificacao:
    cert = (
        db.query(Certificacao)
        .filter(
            Certificacao.id_certificacao == id_certificacao,
            Certificacao.tenant_id == tenant_id,
        )
        .first()
    )
    if not cert:
        raise HTTPException(status_code=404, detail="Certificação não encontrada")
    return cert


def _validar_status(status: str) -> None:
    if status not in _STATUS_CERTIFICACAO:
        raise HTTPException(
            status_code=422,
            detail="Status deve ser PENDENTE, VIGENTE, VENCIDA ou REVOGADA",
        )


# ── Certificações ────────────────────────────────────────────────────────────


@router.get("/api/certificacoes", response_model=list[CertificacaoOut])
def listar_certificacoes(
    status: str | None = Query(None),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    q = db.query(Certificacao).filter(Certificacao.tenant_id == usuario.tenant_id)
    if status:
        q = q.filter(Certificacao.status == status)

    certs = q.order_by(Certificacao.nome_certificacao).all()
    por_cert, acoes_por_cert = _contagens(db, usuario.tenant_id)
    return [
        _montar_certificacao(
            c,
            por_cert.get(c.id_certificacao, 0),
            acoes_por_cert.get(c.id_certificacao, 0),
        )
        for c in certs
    ]


@router.get("/api/certificacoes/{id_certificacao}", response_model=CertificacaoOut)
def obter_certificacao(
    id_certificacao: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    cert = _buscar_certificacao(db, id_certificacao, usuario.tenant_id)
    por_cert, acoes_por_cert = _contagens(db, usuario.tenant_id)
    return _montar_certificacao(
        cert,
        por_cert.get(cert.id_certificacao, 0),
        acoes_por_cert.get(cert.id_certificacao, 0),
    )


@router.post("/api/certificacoes", response_model=CertificacaoOut, status_code=201)
def criar_certificacao(
    payload: CertificacaoCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(_admin),
):
    _validar_status(payload.status)

    conflito = (
        db.query(Certificacao)
        .filter(
            Certificacao.tenant_id == usuario.tenant_id,
            Certificacao.nome_certificacao == payload.nome_certificacao,
        )
        .first()
    )
    if conflito:
        raise HTTPException(
            status_code=409,
            detail="Já existe uma certificação com esse nome para este ente",
        )

    cert = Certificacao(tenant_id=usuario.tenant_id, **payload.model_dump())
    db.add(cert)
    db.commit()
    db.refresh(cert)
    return _montar_certificacao(cert)


@router.put("/api/certificacoes/{id_certificacao}", response_model=CertificacaoOut)
def atualizar_certificacao(
    id_certificacao: int,
    payload: CertificacaoUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(_admin),
):
    cert = _buscar_certificacao(db, id_certificacao, usuario.tenant_id)

    dados = payload.model_dump(exclude_unset=True)
    if "status" in dados:
        _validar_status(dados["status"])

    nome = dados.get("nome_certificacao")
    if nome is not None and nome != cert.nome_certificacao:
        conflito = (
            db.query(Certificacao)
            .filter(
                Certificacao.tenant_id == usuario.tenant_id,
                Certificacao.nome_certificacao == nome,
                Certificacao.id_certificacao != cert.id_certificacao,
            )
            .first()
        )
        if conflito:
            raise HTTPException(
                status_code=409,
                detail="Já existe uma certificação com esse nome para este ente",
            )

    for campo, valor in dados.items():
        setattr(cert, campo, valor)
    db.commit()
    db.refresh(cert)
    por_cert, acoes_por_cert = _contagens(db, usuario.tenant_id)
    return _montar_certificacao(
        cert,
        por_cert.get(cert.id_certificacao, 0),
        acoes_por_cert.get(cert.id_certificacao, 0),
    )


@router.delete("/api/certificacoes/{id_certificacao}", status_code=204)
def remover_certificacao(
    id_certificacao: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(_admin),
):
    cert = _buscar_certificacao(db, id_certificacao, usuario.tenant_id)
    qtd = db.query(func.count(Auditoria.id)).filter(
        Auditoria.id_certificacao == cert.id_certificacao
    ).scalar()
    if qtd:
        raise HTTPException(
            status_code=409,
            detail="A certificação possui auditorias vinculadas",
        )
    db.delete(cert)
    db.commit()


# ── Auditorias ───────────────────────────────────────────────────────────────


def _montar_auditoria(a: Auditoria, acoes_count: int = 0) -> AuditoriaOut:
    cert = a.certificacao
    return AuditoriaOut(
        id=a.id,
        id_certificacao=a.id_certificacao,
        id_manual=a.id_manual,
        tipo=a.tipo,
        modalidade=a.modalidade,
        data_auditoria=a.data_auditoria,
        duracao_horas=a.duracao_horas,
        nivel_recomendado=a.nivel_recomendado,
        parecer_geral=a.parecer_geral,
        conclusao=a.conclusao,
        auditor_nome=a.auditor_nome,
        auditor_email=a.auditor_email,
        criado_em=a.criado_em,
        atualizado_em=a.atualizado_em,
        nome_certificacao=cert.nome_certificacao if cert else "",
        nome_manual=a.manual.nome_manual if a.manual else "",
        versao_manual=a.manual.versao_manual if a.manual else "",
        acoes_count=acoes_count,
    )


def _buscar_auditoria(db: Session, id_auditoria: str, tenant_id: str) -> Auditoria:
    aud = (
        db.query(Auditoria)
        .filter(Auditoria.id == id_auditoria, Auditoria.tenant_id == tenant_id)
        .first()
    )
    if not aud:
        raise HTTPException(status_code=404, detail="Auditoria não encontrada")
    return aud


def _validar_vinculos(
    db: Session,
    tenant_id: str,
    *,
    id_certificacao: int,
    id_manual: int,
) -> None:
    cert = (
        db.query(Certificacao)
        .filter(
            Certificacao.id_certificacao == id_certificacao,
            Certificacao.tenant_id == tenant_id,
        )
        .first()
    )
    if not cert:
        raise HTTPException(status_code=422, detail="Certificação não encontrada")
    if not db.get(Manual, id_manual):
        raise HTTPException(status_code=422, detail="Manual não encontrado")


@router.get("/api/auditorias", response_model=list[AuditoriaOut])
def listar_auditorias(
    id_certificacao: int | None = Query(None),
    id_manual: int | None = Query(None),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    q = db.query(Auditoria).filter(Auditoria.tenant_id == usuario.tenant_id)
    if id_certificacao is not None:
        q = q.filter(Auditoria.id_certificacao == id_certificacao)
    if id_manual is not None:
        q = q.filter(Auditoria.id_manual == id_manual)

    auds = (
        q.options(
            joinedload(Auditoria.certificacao),
            joinedload(Auditoria.manual),
        )
        .order_by(Auditoria.data_auditoria.desc(), Auditoria.id)
        .all()
    )
    if not auds:
        return []
    contagens = dict(
        db.query(Acao.id_auditoria, func.count(Acao.id_acao))
        .filter(Acao.id_auditoria.in_([a.id for a in auds]))
        .group_by(Acao.id_auditoria)
        .all()
    )
    return [_montar_auditoria(a, contagens.get(a.id, 0)) for a in auds]


@router.get("/api/auditorias/{id_auditoria}", response_model=AuditoriaOut)
def obter_auditoria(
    id_auditoria: str,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    aud = _buscar_auditoria(db, id_auditoria, usuario.tenant_id)
    qtd = db.query(func.count(Acao.id_acao)).filter(Acao.id_auditoria == aud.id).scalar()
    return _montar_auditoria(aud, qtd or 0)


@router.post("/api/auditorias", response_model=AuditoriaOut, status_code=201)
def criar_auditoria(
    payload: AuditoriaCreate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(_admin),
):
    _validar_vinculos(
        db,
        usuario.tenant_id,
        id_certificacao=payload.id_certificacao,
        id_manual=payload.id_manual,
    )
    aud = Auditoria(
        tenant_id=usuario.tenant_id,
        criado_por=usuario.id,
        **payload.model_dump(),
    )
    db.add(aud)
    db.commit()
    db.refresh(aud)
    return _montar_auditoria(aud)


@router.put("/api/auditorias/{id_auditoria}", response_model=AuditoriaOut)
def atualizar_auditoria(
    id_auditoria: str,
    payload: AuditoriaUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(_admin),
):
    aud = _buscar_auditoria(db, id_auditoria, usuario.tenant_id)
    dados = payload.model_dump(exclude_unset=True)

    id_certificacao = dados.get("id_certificacao", aud.id_certificacao)
    id_manual = dados.get("id_manual", aud.id_manual)
    mudou_escopo = id_manual != aud.id_manual

    _validar_vinculos(
        db,
        usuario.tenant_id,
        id_certificacao=id_certificacao,
        id_manual=id_manual,
    )

    if mudou_escopo:
        qtd = db.query(func.count(Acao.id_acao)).filter(Acao.id_auditoria == aud.id).scalar()
        if qtd:
            raise HTTPException(
                status_code=409,
                detail="A auditoria possui ações vinculadas; não é possível alterar o manual",
            )

    for campo, valor in dados.items():
        setattr(aud, campo, valor)
    db.commit()
    db.refresh(aud)

    qtd = db.query(func.count(Acao.id_acao)).filter(Acao.id_auditoria == aud.id).scalar()
    return _montar_auditoria(aud, qtd or 0)


@router.delete("/api/auditorias/{id_auditoria}", status_code=204)
def remover_auditoria(
    id_auditoria: str,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(_admin),
):
    aud = _buscar_auditoria(db, id_auditoria, usuario.tenant_id)
    qtd = db.query(func.count(Acao.id_acao)).filter(Acao.id_auditoria == aud.id).scalar()
    if qtd:
        raise HTTPException(
            status_code=409,
            detail="A auditoria possui ações vinculadas",
        )
    db.delete(aud)
    db.commit()
