"""Diagnóstico Pró-Gestão: requisitos do manual.

Mantém o formato legado consumido pela tela de Progestão (cod/dimensao/titulo),
derivado das novas tabelas `requisito` + `dimensao`. A dimensão abreviada
(CI/GC/EP) sai do prefixo do código do requisito.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_usuario_atual
from app.db import get_db
from app.models import Requisito, Usuario

router = APIRouter(prefix="/api/requisitos", tags=["Diagnóstico"])

# Prefixo do cod_requisito -> sigla de dimensão usada pela UI legada.
_PREFIXO_DIMENSAO = {"3.1": "CI", "3.2": "GC", "3.3": "EP"}


def _dimensao_abreviada(cod_requisito: str) -> str:
    return _PREFIXO_DIMENSAO.get(cod_requisito.rsplit(".", 1)[0], "CI")


@router.get("")
def listar_requisitos(
    dimensao: str | None = Query(None),
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_usuario_atual),
):
    q = db.query(Requisito).options(joinedload(Requisito.dimensao))
    reqs = q.order_by(Requisito.cod_requisito).all()

    result = []
    for r in reqs:
        dim = _dimensao_abreviada(r.cod_requisito)
        if dimensao and dim != dimensao:
            continue
        result.append(
            {
                "id_requisito": r.id_requisito,
                "cod": r.cod_requisito,
                "dimensao": dim,
                "titulo": r.nome_requisito,
                "nome_dimensao": r.dimensao.nome_dimensao if r.dimensao else "",
            }
        )
    return result
