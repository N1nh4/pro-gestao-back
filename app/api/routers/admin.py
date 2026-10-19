"""Administração: usuários, perfis e unidades."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_usuario_atual
from app.core.security import hash_senha
from app.db import get_db
from app.models import Perfil, Tenant, Unidade, Usuario, UsuarioUnidadePerfil
from app.schemas import (
    EnteOut,
    EnteUpdate,
    PerfilCreate,
    UnidadeCreate,
    UnidadeUpdate,
    UsuarioCreate,
    UsuarioUpdate,
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

        unidades_ids = list({v.unidade_id for v in vinculos if v.unidade_id})
        unidades = (
            db.query(Unidade).filter(Unidade.id.in_(unidades_ids)).all()
            if unidades_ids
            else []
        )

        result.append(
            {
                "id": u.id,
                "id_usuario": u.id_usuario,
                "login": u.login,
                "email": u.email,
                "nome_completo": u.nome_completo,
                "status": u.status,
                "perfis": [{"id": p.id, "nome": p.nome} for p in perfis],
                "unidades": [{"id": un.id, "sigla": un.sigla} for un in unidades],
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
    perfis = req.perfil_ids or [req.perfil_id]
    for perfil_id in perfis:
        for uid in unidades:
            db.add(
                UsuarioUnidadePerfil(
                    usuario_id=novo.id,
                    unidade_id=uid,
                    perfil_id=perfil_id,
                    concedido_por=atual.id,
                )
            )

    db.commit()
    db.refresh(novo)
    return {"id": novo.id, "login": login, "id_usuario": id_usuario}


@router.put("/api/usuarios/{usuario_id}")
def atualizar_usuario(
    usuario_id: str,
    req: UsuarioUpdate,
    db: Session = Depends(get_db),
    atual: Usuario = Depends(get_usuario_atual),
):
    alvo = (
        db.query(Usuario)
        .filter(Usuario.id == usuario_id, Usuario.tenant_id == atual.tenant_id)
        .first()
    )
    if not alvo:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    dados = req.model_dump(exclude_unset=True)

    if "email" in dados and dados["email"]:
        email = dados["email"].lower()
        existe = (
            db.query(Usuario)
            .filter(
                Usuario.tenant_id == atual.tenant_id,
                Usuario.email == email,
                Usuario.id != alvo.id,
            )
            .first()
        )
        if existe:
            raise HTTPException(status_code=400, detail="E-mail já cadastrado neste ente")
        alvo.email = email

    if dados.get("nome_completo"):
        alvo.nome_completo = dados["nome_completo"]
    if dados.get("status"):
        alvo.status = dados["status"]
    if dados.get("senha"):
        alvo.senha_hash = hash_senha(dados["senha"])

    if "perfil_id" in dados or "perfil_ids" in dados or "unidade_ids" in dados:
        vinculos_atuais = (
            db.query(UsuarioUnidadePerfil)
            .filter(UsuarioUnidadePerfil.usuario_id == alvo.id)
            .all()
        )

        if "perfil_ids" in dados:
            perfis_alvo = dados.get("perfil_ids") or []
        elif "perfil_id" in dados:
            perfis_alvo = [dados["perfil_id"]] if dados["perfil_id"] else []
        else:
            perfis_alvo = list({v.perfil_id for v in vinculos_atuais})
        if not perfis_alvo:
            raise HTTPException(status_code=400, detail="Informe ao menos um perfil")

        if "unidade_ids" in dados:
            unidades_alvo = dados.get("unidade_ids") or [None]
        else:
            unidades_alvo = list({v.unidade_id for v in vinculos_atuais}) or [None]

        db.query(UsuarioUnidadePerfil).filter(
            UsuarioUnidadePerfil.usuario_id == alvo.id
        ).delete()

        for perfil_id in perfis_alvo:
            for uid in unidades_alvo:
                db.add(
                    UsuarioUnidadePerfil(
                        usuario_id=alvo.id,
                        unidade_id=uid,
                        perfil_id=perfil_id,
                        concedido_por=atual.id,
                    )
                )

    db.commit()
    db.refresh(alvo)
    return {"id": alvo.id, "email": alvo.email, "nome_completo": alvo.nome_completo}


@router.get("/api/ente", response_model=EnteOut)
def obter_ente(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    tenant = db.get(Tenant, usuario.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Ente não encontrado")
    return tenant


@router.put("/api/ente", response_model=EnteOut)
def atualizar_ente(
    req: EnteUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    tenant = db.get(Tenant, usuario.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Ente não encontrado")

    dados = req.model_dump(exclude_unset=True)

    if dados.get("cnpj_ente"):
        outro = (
            db.query(Tenant)
            .filter(Tenant.cnpj_ente == dados["cnpj_ente"], Tenant.id != tenant.id)
            .first()
        )
        if outro:
            raise HTTPException(status_code=400, detail="CNPJ já cadastrado por outro ente")

    inicio = dados.get("data_inicio_processo", tenant.data_inicio_processo)
    fim = dados.get("data_fim_processo", tenant.data_fim_processo)
    if inicio and fim and fim < inicio:
        raise HTTPException(
            status_code=400,
            detail="A data fim do processo não pode ser anterior à data de início",
        )

    for campo, valor in dados.items():
        setattr(tenant, campo, valor)

    db.commit()
    db.refresh(tenant)
    return tenant


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


@router.put("/api/unidades/{unidade_id}")
def atualizar_unidade(
    unidade_id: str,
    req: UnidadeUpdate,
    db: Session = Depends(get_db),
    atual: Usuario = Depends(get_usuario_atual),
):
    unidade = (
        db.query(Unidade)
        .filter(Unidade.id == unidade_id, Unidade.tenant_id == atual.tenant_id)
        .first()
    )
    if not unidade:
        raise HTTPException(status_code=404, detail="Unidade não encontrada")

    dados = req.model_dump(exclude_unset=True)

    if dados.get("sigla"):
        sigla = dados["sigla"].upper()
        existe = (
            db.query(Unidade)
            .filter(
                Unidade.tenant_id == atual.tenant_id,
                Unidade.sigla == sigla,
                Unidade.id != unidade.id,
            )
            .first()
        )
        if existe:
            raise HTTPException(status_code=400, detail="Sigla já utilizada neste ente")
        unidade.sigla = sigla

    if "nome" in dados and dados["nome"]:
        unidade.nome = dados["nome"]
    if "descricao" in dados:
        unidade.descricao = dados["descricao"]
    if "ativo" in dados and dados["ativo"] is not None:
        unidade.ativo = dados["ativo"]

    db.commit()
    db.refresh(unidade)
    return {
        "id": unidade.id,
        "sigla": unidade.sigla,
        "nome": unidade.nome,
        "descricao": unidade.descricao,
    }
