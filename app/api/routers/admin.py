"""Administração: usuários, perfis e unidades."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_usuario_atual
from app.core.security import hash_senha
from app.db import get_db
from app.models import Perfil, Unidade, Usuario, UsuarioUnidadePerfil
from app.schemas import (
    PerfilCreate,
    UnidadeCreate,
    UsuarioCreate,
)

router = APIRouter(tags=["Administração"])


def _slug_login(nome_completo: str) -> str:
    partes = (
        nome_completo.strip()
        .lower()
        .replace("á", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("ã", "a")
        .replace("ç", "c")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("í", "i")
        .replace("â", "a")
        .split()
    )
    return f"{partes[0]}.{partes[-1]}" if len(partes) >= 2 else partes[0]


@router.get("/api/usuarios")
def listar_usuarios(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    usuarios = (
        db.query(Usuario)
        .filter(Usuario.tenant_id == usuario.tenant_id)
        .order_by(Usuario.id_usuario)
        .all()
    )

    result = []
    for u in usuarios:
        vinculos = (
            db.query(UsuarioUnidadePerfil)
            .filter(UsuarioUnidadePerfil.usuario_id == u.id)
            .all()
        )
        perfis_ids = list({v.perfil_id for v in vinculos})
        perfis = db.query(Perfil).filter(Perfil.id.in_(perfis_ids)).all()

        result.append(
            {
                "id": u.id,
                "id_usuario": u.id_usuario,
                "login": u.login,
                "email": u.email,
                "nome_completo": u.nome_completo,
                "status": u.status,
                "perfis": [{"id": p.id, "nome": p.nome} for p in perfis],
                "criado_em": u.criado_em,
            }
        )
    return result


@router.post("/api/usuarios")
def criar_usuario(
    req: UsuarioCreate,
    db: Session = Depends(get_db),
    atual: Usuario = Depends(get_usuario_atual),
):
    login = _slug_login(req.nome_completo)

    existe = (
        db.query(Usuario)
        .filter(
            Usuario.tenant_id == atual.tenant_id,
            Usuario.email == req.email.lower(),
        )
        .first()
    )
    if existe:
        raise HTTPException(status_code=400, detail="E-mail já cadastrado neste ente")

    ultimo = (
        db.query(func.count(Usuario.id))
        .filter(Usuario.tenant_id == atual.tenant_id)
        .scalar()
        or 0
    )
    id_usuario = str(ultimo + 1).zfill(3)

    novo = Usuario(
        id_usuario=id_usuario,
        tenant_id=atual.tenant_id,
        login=login,
        email=req.email.lower(),
        nome_completo=req.nome_completo,
        senha_hash=hash_senha(req.senha),
        criado_por=atual.id,
    )
    db.add(novo)
    db.flush()

    unidades = req.unidade_ids or [None]
    for uid in unidades:
        db.add(
            UsuarioUnidadePerfil(
                usuario_id=novo.id,
                unidade_id=uid,
                perfil_id=req.perfil_id,
                concedido_por=atual.id,
            )
        )

    db.commit()
    db.refresh(novo)
    return {"id": novo.id, "login": login, "id_usuario": id_usuario}


@router.get("/api/perfis")
def listar_perfis(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    perfis = (
        db.query(Perfil)
        .filter(
            (Perfil.tenant_id == usuario.tenant_id) | (Perfil.tenant_id.is_(None)),
            Perfil.ativo.is_(True),
        )
        .order_by(Perfil.nome)
        .all()
    )
    return [
        {
            "id": p.id,
            "nome": p.nome,
            "descricao": p.descricao,
            "tipo": p.tipo,
            "requer_setor": p.requer_setor,
        }
        for p in perfis
    ]


@router.post("/api/perfis")
def criar_perfil(
    req: PerfilCreate,
    db: Session = Depends(get_db),
    atual: Usuario = Depends(get_usuario_atual),
):
    novo = Perfil(
        tenant_id=atual.tenant_id,
        nome=req.nome,
        descricao=req.descricao,
        tipo="customizado",
        requer_setor=req.requer_setor,
        criado_por=atual.id,
    )
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return {"id": novo.id, "nome": novo.nome}


@router.get("/api/unidades")
def listar_unidades(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    unidades = (
        db.query(Unidade)
        .filter(
            Unidade.tenant_id == usuario.tenant_id,
            Unidade.ativo.is_(True),
        )
        .order_by(Unidade.sigla)
        .all()
    )
    return [
        {"id": u.id, "sigla": u.sigla, "nome": u.nome, "descricao": u.descricao}
        for u in unidades
    ]


@router.post("/api/unidades")
def criar_unidade(
    req: UnidadeCreate,
    db: Session = Depends(get_db),
    atual: Usuario = Depends(get_usuario_atual),
):
    nova = Unidade(
        tenant_id=atual.tenant_id,
        sigla=req.sigla.upper(),
        nome=req.nome,
        descricao=req.descricao,
        criado_por=atual.id,
    )
    db.add(nova)
    db.commit()
    db.refresh(nova)
    return {"id": nova.id, "sigla": nova.sigla, "nome": nova.nome}
