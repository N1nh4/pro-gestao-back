"""Autenticação: login e dados do usuário logado."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_usuario_atual
from app.core.security import criar_token, verificar_senha
from app.db import get_db
from app.models import Perfil, Unidade, Usuario, UsuarioUnidadePerfil
from app.schemas import LoginRequest, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    """Login com e-mail e senha. Retorna JWT."""
    usuario = (
        db.query(Usuario)
        .filter(
            Usuario.email == req.email.lower().strip(),
            Usuario.status == "ativo",
        )
        .first()
    )

    if not usuario or not verificar_senha(req.senha, usuario.senha_hash):
        raise HTTPException(status_code=401, detail="Usuário ou senha inválidos")

    usuario.ultimo_acesso = datetime.utcnow()
    db.commit()

    vinculos = (
        db.query(UsuarioUnidadePerfil)
        .filter(UsuarioUnidadePerfil.usuario_id == usuario.id)
        .all()
    )
    perfis_ids = list({v.perfil_id for v in vinculos})
    unidade_ids = list({v.unidade_id for v in vinculos if v.unidade_id})

    perfis_db = db.query(Perfil).filter(Perfil.id.in_(perfis_ids)).all()
    perfis_nomes = [p.nome for p in perfis_db]

    unidades_db = db.query(Unidade).filter(Unidade.id.in_(unidade_ids)).all()
    unidades_list = [{"id": u.id, "sigla": u.sigla, "nome": u.nome} for u in unidades_db]

    token = criar_token(
        {
            "sub": usuario.id,
            "tenant_id": usuario.tenant_id,
            "email": usuario.email,
            "perfis": perfis_nomes,
        }
    )

    return TokenResponse(
        access_token=token,
        usuario_id=usuario.id,
        nome=usuario.nome_completo,
        email=usuario.email,
        perfis=perfis_nomes,
        unidades=unidades_list,
    )


@router.get("/me")
def me(usuario: Usuario = Depends(get_usuario_atual), db: Session = Depends(get_db)):
    """Retorna dados do usuário logado."""
    vinculos = (
        db.query(UsuarioUnidadePerfil)
        .filter(UsuarioUnidadePerfil.usuario_id == usuario.id)
        .all()
    )
    perfis_ids = list({v.perfil_id for v in vinculos})
    perfis = db.query(Perfil).filter(Perfil.id.in_(perfis_ids)).all()

    return {
        "id": usuario.id,
        "id_usuario": usuario.id_usuario,
        "login": usuario.login,
        "email": usuario.email,
        "nome_completo": usuario.nome_completo,
        "status": usuario.status,
        "perfis": [{"id": p.id, "nome": p.nome, "tipo": p.tipo} for p in perfis],
        "ultimo_acesso": usuario.ultimo_acesso,
    }
