"""Diagnóstico Pró-Gestão: requisitos do manual."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_usuario_atual
from app.db import get_db
from app.models import Requisito, Usuario

router = APIRouter(prefix="/api/requisitos", tags=["Diagnóstico"])


@router.get("")
def listar_requisitos(
    dimensao: str | None = Query(None),
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_usuario_atual),
):
    q = db.query(Requisito)
    if dimensao:
        q = q.filter(Requisito.dimensao == dimensao)
    reqs = q.order_by(Requisito.cod).all()
    return [
        {
            "cod": r.cod,
            "dimensao": r.dimensao,
            "titulo": r.titulo,
            "essencial": r.essencial,
            "nivel_minimo": r.nivel_minimo,
            "descricao_nivel_i": r.descricao_nivel_i,
            "descricao_nivel_ii": r.descricao_nivel_ii,
            "descricao_nivel_iii": r.descricao_nivel_iii,
            "descricao_nivel_iv": r.descricao_nivel_iv,
        }
        for r in reqs
    ]
