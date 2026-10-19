"""Dependências compartilhadas da API (auth, sessão, RBAC)."""

from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import JWTError, decodificar_token
from app.db import get_db
from app.models import Perfil, Usuario, UsuarioUnidadePerfil

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_usuario_atual(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    """Retorna o usuário autenticado (objeto ORM) a partir do JWT."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token não fornecido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decodificar_token(token)
        usuario_id: str | None = payload.get("sub")
        if not usuario_id:
            raise HTTPException(status_code=401, detail="Token inválido")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token expirado ou inválido") from None

    usuario = (
        db.query(Usuario)
        .filter(Usuario.id == usuario_id, Usuario.status == "ativo")
        .first()
    )
    if not usuario:
        raise HTTPException(status_code=401, detail="Usuário não encontrado ou inativo")
    return usuario


def nomes_perfis(db: Session, usuario: Usuario) -> set[str]:
    """Nomes dos perfis vinculados ao usuário."""
    vinculos = (
        db.query(UsuarioUnidadePerfil)
        .filter(UsuarioUnidadePerfil.usuario_id == usuario.id)
        .all()
    )
    perfis_ids = {v.perfil_id for v in vinculos}
    if not perfis_ids:
        return set()
    perfis = db.query(Perfil).filter(Perfil.id.in_(perfis_ids)).all()
    return {p.nome for p in perfis}


def requer_perfil(*perfis_permitidos: str) -> Callable[..., Usuario]:
    """Dependency factory: exige que o usuário tenha um dos perfis informados."""

    def _check(
        usuario: Usuario = Depends(get_usuario_atual),
        db: Session = Depends(get_db),
    ) -> Usuario:
        if nomes_perfis(db, usuario).intersection(perfis_permitidos):
            return usuario
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Acesso negado. Perfil necessário: {perfis_permitidos}",
        )

    return _check
