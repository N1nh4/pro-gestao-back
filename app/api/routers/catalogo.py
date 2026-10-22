"""Catálogo do manual: CRUD de manual, dimensões, requisitos e itens.

O catálogo é referência compartilhada (não é dado de um tenant), por isso os
endpoints de escrita exigem perfil de administrador.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_usuario_atual, requer_perfil
from app.db import get_db
from app.models import Acao, Auditoria, Dimensao, Item, Manual, Nivel, Requisito, Usuario
from app.schemas import (
    DimensaoCreate,
    DimensaoOut,
    DimensaoUpdate,
    ItemCreate,
    ItemOut,
    ItemUpdate,
    ManualCreate,
    ManualOut,
    ManualUpdate,
    NivelCreate,
    NivelOut,
    NivelUpdate,
    RequisitoCatalogoOut,
    RequisitoCreate,
    RequisitoUpdate,
)

router = APIRouter(prefix="/api/catalogo", tags=["Catálogo do Manual"])

# Escrita no catálogo é restrita a administradores (mesmo corte da UI de Config).
_admin = requer_perfil("Admin Master", "Admin do Ente")

_NIVEIS_VALIDOS = {"I", "II", "III", "IV"}


def _cod_requisito_valido(cod: str) -> bool:
    partes = cod.split(".")
    return bool(partes) and all(p.isdigit() for p in partes)


# ── MANUAIS ──────────────────────────────────────────────────────


@router.get("/manuais", response_model=list[ManualOut])
def listar_manuais(
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_usuario_atual),
):
    return db.query(Manual).order_by(Manual.versao_manual.desc()).all()


@router.post("/manuais", response_model=ManualOut, status_code=201)
def criar_manual(
    req: ManualCreate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_admin),
):
    existe = db.query(Manual).filter(Manual.versao_manual == req.versao_manual).first()
    if existe:
        raise HTTPException(status_code=409, detail="Já existe um manual com essa versão")
    manual = Manual(**req.model_dump())
    db.add(manual)
    db.commit()
    db.refresh(manual)
    return manual


@router.put("/manuais/{id_manual}", response_model=ManualOut)
def atualizar_manual(
    id_manual: int,
    req: ManualUpdate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_admin),
):
    manual = db.get(Manual, id_manual)
    if not manual:
        raise HTTPException(status_code=404, detail="Manual não encontrado")
    dados = req.model_dump(exclude_unset=True)
    if "versao_manual" in dados:
        conflito = (
            db.query(Manual)
            .filter(Manual.versao_manual == dados["versao_manual"], Manual.id_manual != id_manual)
            .first()
        )
        if conflito:
            raise HTTPException(status_code=409, detail="Já existe um manual com essa versão")
    for campo, valor in dados.items():
        setattr(manual, campo, valor)
    db.commit()
    db.refresh(manual)
    return manual


@router.delete("/manuais/{id_manual}", status_code=204)
def remover_manual(
    id_manual: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_admin),
):
    manual = db.get(Manual, id_manual)
    if not manual:
        raise HTTPException(status_code=404, detail="Manual não encontrado")
    qtd = db.query(func.count(Requisito.id_requisito)).filter(Requisito.id_manual == id_manual).scalar()
    if qtd:
        raise HTTPException(status_code=409, detail="Manual possui requisitos vinculados")
    qtd = db.query(func.count(Auditoria.id)).filter(Auditoria.id_manual == id_manual).scalar()
    if qtd:
        raise HTTPException(status_code=409, detail="Manual possui auditorias vinculadas")
    db.delete(manual)
    db.commit()


# ── DIMENSÕES ────────────────────────────────────────────────────


@router.get("/dimensoes", response_model=list[DimensaoOut])
def listar_dimensoes(
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_usuario_atual),
):
    return db.query(Dimensao).order_by(Dimensao.nome_dimensao).all()


@router.post("/dimensoes", response_model=DimensaoOut, status_code=201)
def criar_dimensao(
    req: DimensaoCreate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_admin),
):
    existe = (
        db.query(Dimensao).filter(Dimensao.nome_dimensao == req.nome_dimensao).first()
    )
    if existe:
        raise HTTPException(status_code=409, detail="Já existe uma dimensão com esse nome")
    dimensao = Dimensao(**req.model_dump())
    db.add(dimensao)
    db.commit()
    db.refresh(dimensao)
    return dimensao


@router.put("/dimensoes/{id_dimensao}", response_model=DimensaoOut)
def atualizar_dimensao(
    id_dimensao: int,
    req: DimensaoUpdate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_admin),
):
    dimensao = db.get(Dimensao, id_dimensao)
    if not dimensao:
        raise HTTPException(status_code=404, detail="Dimensão não encontrada")
    dados = req.model_dump(exclude_unset=True)
    if "nome_dimensao" in dados:
        conflito = (
            db.query(Dimensao)
            .filter(
                Dimensao.nome_dimensao == dados["nome_dimensao"],
                Dimensao.id_dimensao != id_dimensao,
            )
            .first()
        )
        if conflito:
            raise HTTPException(status_code=409, detail="Já existe uma dimensão com esse nome")
    for campo, valor in dados.items():
        setattr(dimensao, campo, valor)
    db.commit()
    db.refresh(dimensao)
    return dimensao


@router.delete("/dimensoes/{id_dimensao}", status_code=204)
def remover_dimensao(
    id_dimensao: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_admin),
):
    dimensao = db.get(Dimensao, id_dimensao)
    if not dimensao:
        raise HTTPException(status_code=404, detail="Dimensão não encontrada")
    qtd = (
        db.query(func.count(Requisito.id_requisito))
        .filter(Requisito.id_dimensao == id_dimensao)
        .scalar()
    )
    if qtd:
        raise HTTPException(status_code=409, detail="Dimensão possui requisitos vinculados")
    db.delete(dimensao)
    db.commit()


# ── REQUISITOS ───────────────────────────────────────────────────


def _montar_requisito_out(r: Requisito, total_itens: int) -> RequisitoCatalogoOut:
    return RequisitoCatalogoOut(
        id_requisito=r.id_requisito,
        id_manual=r.id_manual,
        id_dimensao=r.id_dimensao,
        cod_requisito=r.cod_requisito,
        nome_requisito=r.nome_requisito,
        nome_dimensao=r.dimensao.nome_dimensao if r.dimensao else "",
        total_itens=total_itens,
    )


@router.get("/requisitos", response_model=list[RequisitoCatalogoOut])
def listar_requisitos(
    id_manual: int | None = Query(None),
    id_dimensao: int | None = Query(None),
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_usuario_atual),
):
    q = db.query(Requisito)
    if id_manual is not None:
        q = q.filter(Requisito.id_manual == id_manual)
    if id_dimensao is not None:
        q = q.filter(Requisito.id_dimensao == id_dimensao)
    reqs = q.order_by(Requisito.cod_requisito).all()
    if not reqs:
        return []

    contagens = dict(
        db.query(Item.id_requisito, func.count(Item.id_item))
        .filter(Item.id_requisito.in_([r.id_requisito for r in reqs]))
        .group_by(Item.id_requisito)
        .all()
    )
    return [_montar_requisito_out(r, contagens.get(r.id_requisito, 0)) for r in reqs]


@router.post("/requisitos", response_model=RequisitoCatalogoOut, status_code=201)
def criar_requisito(
    req: RequisitoCreate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_admin),
):
    if not _cod_requisito_valido(req.cod_requisito):
        raise HTTPException(status_code=422, detail="Código inválido. Use formato 3.1.1")
    if not db.get(Manual, req.id_manual):
        raise HTTPException(status_code=422, detail="Manual não encontrado")
    if not db.get(Dimensao, req.id_dimensao):
        raise HTTPException(status_code=422, detail="Dimensão não encontrada")

    conflito = (
        db.query(Requisito)
        .filter(
            Requisito.id_manual == req.id_manual,
            Requisito.cod_requisito == req.cod_requisito,
        )
        .first()
    )
    if conflito:
        raise HTTPException(
            status_code=409, detail="Já existe requisito com esse código neste manual"
        )

    requisito = Requisito(**req.model_dump())
    db.add(requisito)
    db.commit()
    db.refresh(requisito)
    return _montar_requisito_out(requisito, 0)


@router.put("/requisitos/{id_requisito}", response_model=RequisitoCatalogoOut)
def atualizar_requisito(
    id_requisito: int,
    req: RequisitoUpdate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_admin),
):
    requisito = db.get(Requisito, id_requisito)
    if not requisito:
        raise HTTPException(status_code=404, detail="Requisito não encontrado")
    dados = req.model_dump(exclude_unset=True)

    if "cod_requisito" in dados and not _cod_requisito_valido(dados["cod_requisito"]):
        raise HTTPException(status_code=422, detail="Código inválido. Use formato 3.1.1")
    if "id_manual" in dados and not db.get(Manual, dados["id_manual"]):
        raise HTTPException(status_code=422, detail="Manual não encontrado")
    if "id_dimensao" in dados and not db.get(Dimensao, dados["id_dimensao"]):
        raise HTTPException(status_code=422, detail="Dimensão não encontrada")

    if "cod_requisito" in dados or "id_manual" in dados:
        novo_cod = dados.get("cod_requisito", requisito.cod_requisito)
        novo_manual = dados.get("id_manual", requisito.id_manual)
        conflito = (
            db.query(Requisito)
            .filter(
                Requisito.id_manual == novo_manual,
                Requisito.cod_requisito == novo_cod,
                Requisito.id_requisito != id_requisito,
            )
            .first()
        )
        if conflito:
            raise HTTPException(
                status_code=409, detail="Já existe requisito com esse código neste manual"
            )

    for campo, valor in dados.items():
        setattr(requisito, campo, valor)
    db.commit()
    db.refresh(requisito)

    total_itens = (
        db.query(func.count(Item.id_item))
        .filter(Item.id_requisito == id_requisito)
        .scalar()
        or 0
    )
    return _montar_requisito_out(requisito, total_itens)


@router.delete("/requisitos/{id_requisito}", status_code=204)
def remover_requisito(
    id_requisito: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_admin),
):
    requisito = db.get(Requisito, id_requisito)
    if not requisito:
        raise HTTPException(status_code=404, detail="Requisito não encontrado")
    # Itens caem em cascata (ON DELETE CASCADE). Ações seguem RESTRICT.
    qtd_acoes = (
        db.query(func.count(Acao.id_acao)).filter(Acao.id_requisito == id_requisito).scalar()
    )
    if qtd_acoes:
        raise HTTPException(status_code=409, detail="Requisito possui ações vinculadas")
    db.delete(requisito)
    db.commit()


# ── NÍVEIS ────────────────────────────────────────────────────────


@router.get("/niveis", response_model=list[NivelOut])
def listar_niveis(
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_usuario_atual),
):
    return db.query(Nivel).order_by(Nivel.nome_nivel).all()


@router.post("/niveis", response_model=NivelOut, status_code=201)
def criar_nivel(
    req: NivelCreate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_admin),
):
    existe = db.query(Nivel).filter(Nivel.nome_nivel == req.nome_nivel).first()
    if existe:
        raise HTTPException(status_code=409, detail="Já existe um nível com esse nome")
    nivel = Nivel(**req.model_dump())
    db.add(nivel)
    db.commit()
    db.refresh(nivel)
    return nivel


@router.put("/niveis/{id_nivel}", response_model=NivelOut)
def atualizar_nivel(
    id_nivel: int,
    req: NivelUpdate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_admin),
):
    nivel = db.get(Nivel, id_nivel)
    if not nivel:
        raise HTTPException(status_code=404, detail="Nível não encontrado")
    dados = req.model_dump(exclude_unset=True)
    if "nome_nivel" in dados:
        conflito = (
            db.query(Nivel)
            .filter(Nivel.nome_nivel == dados["nome_nivel"], Nivel.id_nivel != id_nivel)
            .first()
        )
        if conflito:
            raise HTTPException(status_code=409, detail="Já existe um nível com esse nome")
    for campo, valor in dados.items():
        setattr(nivel, campo, valor)
    db.commit()
    db.refresh(nivel)
    return nivel


@router.delete("/niveis/{id_nivel}", status_code=204)
def remover_nivel(
    id_nivel: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_admin),
):
    nivel = db.get(Nivel, id_nivel)
    if not nivel:
        raise HTTPException(status_code=404, detail="Nível não encontrado")
    qtd = db.query(func.count(Item.id_item)).filter(Item.nivel == nivel.nome_nivel).scalar()
    if qtd:
        raise HTTPException(status_code=409, detail="Nível possui itens vinculados")
    db.delete(nivel)
    db.commit()


# ── ITENS ────────────────────────────────────────────────────────


@router.get("/itens", response_model=list[ItemOut])
def listar_itens(
    id_requisito: int | None = Query(None),
    nivel: str | None = Query(None),
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_usuario_atual),
):
    q = db.query(Item)
    if id_requisito is not None:
        q = q.filter(Item.id_requisito == id_requisito)
    if nivel:
        q = q.filter(Item.nivel == nivel)
    return q.order_by(Item.nivel, Item.nome_item).all()


@router.post("/itens", response_model=ItemOut, status_code=201)
def criar_item(
    req: ItemCreate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_admin),
):
    if req.nivel not in _NIVEIS_VALIDOS:
        raise HTTPException(status_code=422, detail="Nível deve ser I, II, III ou IV")
    if not db.get(Requisito, req.id_requisito):
        raise HTTPException(status_code=422, detail="Requisito não encontrado")

    conflito = (
        db.query(Item)
        .filter(
            Item.id_requisito == req.id_requisito,
            Item.nivel == req.nivel,
            Item.nome_item == req.nome_item,
        )
        .first()
    )
    if conflito:
        raise HTTPException(
            status_code=409, detail="Já existe item com esse nome neste nível"
        )

    item = Item(**req.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/itens/{id_item}", response_model=ItemOut)
def atualizar_item(
    id_item: int,
    req: ItemUpdate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_admin),
):
    item = db.get(Item, id_item)
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    dados = req.model_dump(exclude_unset=True)

    if "nivel" in dados and dados["nivel"] not in _NIVEIS_VALIDOS:
        raise HTTPException(status_code=422, detail="Nível deve ser I, II, III ou IV")
    if "id_requisito" in dados and not db.get(Requisito, dados["id_requisito"]):
        raise HTTPException(status_code=422, detail="Requisito não encontrado")

    if "nome_item" in dados or "nivel" in dados or "id_requisito" in dados:
        novo_req = dados.get("id_requisito", item.id_requisito)
        novo_nivel = dados.get("nivel", item.nivel)
        novo_nome = dados.get("nome_item", item.nome_item)
        conflito = (
            db.query(Item)
            .filter(
                Item.id_requisito == novo_req,
                Item.nivel == novo_nivel,
                Item.nome_item == novo_nome,
                Item.id_item != id_item,
            )
            .first()
        )
        if conflito:
            raise HTTPException(
                status_code=409, detail="Já existe item com esse nome neste nível"
            )

    for campo, valor in dados.items():
        setattr(item, campo, valor)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/itens/{id_item}", status_code=204)
def remover_item(
    id_item: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(_admin),
):
    item = db.get(Item, id_item)
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    db.delete(item)
    db.commit()
