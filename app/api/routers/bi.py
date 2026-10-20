"""BI / Painel analítico consolidado."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_usuario_atual
from app.db import get_db
from app.models import Acao, Requisito, Usuario

router = APIRouter(prefix="/api/bi", tags=["BI"])


@router.get("/consolidado")
def bi_consolidado(
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    acoes = (
        db.query(Acao)
        .options(joinedload(Acao.requisito).joinedload(Requisito.dimensao))
        .filter(Acao.tenant_id == usuario.tenant_id)
        .all()
    )
    total = len(acoes)
    aprovadas = sum(1 for a in acoes if a.status == "APROVADO")
    enviadas = sum(1 for a in acoes if a.status == "ENVIADO")
    pendentes = sum(1 for a in acoes if a.status == "PENDENTE")
    em_dilig = sum(1 for a in acoes if a.status == "DILIGÊNCIA")
    pct = round(aprovadas / total * 100, 1) if total else 0

    if aprovadas >= 24:
        nivel = "IV"
    elif aprovadas >= 22:
        nivel = "III"
    elif aprovadas >= 20:
        nivel = "II"
    elif aprovadas >= 18:
        nivel = "I"
    else:
        nivel = "Sem certificação"

    reqs: dict[str, dict[str, int]] = {}
    for a in acoes:
        cod = a.requisito.cod_requisito if a.requisito else ""
        reqs.setdefault(cod, {"total": 0, "aprovadas": 0})
        reqs[cod]["total"] += 1
        if a.status == "APROVADO":
            reqs[cod]["aprovadas"] += 1

    por_req = [
        {"cod": cod, **dados, "pct": round(dados["aprovadas"] / dados["total"] * 100, 1)}
        for cod, dados in sorted(reqs.items())
    ]

    por_dim = {
        "CI": {"total": 0, "aprovadas": 0},
        "GC": {"total": 0, "aprovadas": 0},
        "EP": {"total": 0, "aprovadas": 0},
    }
    prefixo_para_dim = {"3.1": "CI", "3.2": "GC", "3.3": "EP"}
    for a in acoes:
        if not a.requisito:
            continue
        dim = prefixo_para_dim.get(a.requisito.cod_requisito.rsplit(".", 1)[0])
        if dim is None:
            continue
        por_dim[dim]["total"] += 1
        if a.status == "APROVADO":
            por_dim[dim]["aprovadas"] += 1

    return {
        "total_acoes": total,
        "aprovadas": aprovadas,
        "enviadas": enviadas,
        "pendentes": pendentes,
        "diligencias": em_dilig,
        "pct_completude": pct,
        "nivel_estimado": nivel,
        "por_requisito": por_req,
        "por_dimensao": por_dim,
    }
