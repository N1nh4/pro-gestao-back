"""Ações do plano (tabela única `acao`): CRUD e mudança de status.

Tudo por ID: `id_certificacao` → `certificacao`, `id_requisito` → `requisito`,
`id_item` → `item` e `id_unidade` → `unidades`. A ação e o seu plano são o
mesmo registro; os nomes são resolvidos por JOIN, nunca duplicados.
"""

from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_usuario_atual, nomes_perfis, requer_perfil
from app.core.config import get_settings
from app.db import get_db
from app.models import (
    Acao,
    Certificacao,
    Diligencia,
    Documento,
    HistoricoAcao,
    Item,
    Nivel,
    Requisito,
    Unidade,
    Usuario,
    UsuarioUnidadePerfil,
)
from app.schemas import AcaoCreate, AcaoOut, AcaoStatusUpdate, AcaoUpdate

router = APIRouter(prefix="/api/acoes", tags=["Plano de Ação"])

_PERFIS_ADMIN = {"Admin do Ente", "Admin Master"}
_admin = requer_perfil("Admin Master", "Admin do Ente")
_STATUS_VALIDOS = {"PENDENTE", "ENVIADO", "APROVADO", "DILIGÊNCIA"}
_PREFIXO_DIMENSAO = {"CI": "3.1", "GC": "3.2", "EP": "3.3"}
_EXTENSOES_DOCUMENTO = {".pdf", ".docx", ".xlsx"}
_MAX_DOCUMENTO_BYTES = 20 * 1024 * 1024


def _unidades_do_usuario(db: Session, usuario: Usuario) -> list[str]:
    return [
        v.unidade_id
        for v in db.query(UsuarioUnidadePerfil)
        .filter(UsuarioUnidadePerfil.usuario_id == usuario.id)
        .all()
        if v.unidade_id
    ]


def _montar_out(db: Session, a: Acao) -> AcaoOut:
    hist = (
        db.query(HistoricoAcao)
        .filter(HistoricoAcao.acao_id == a.id_acao)
        .order_by(HistoricoAcao.data_evento.desc())
        .all()
    )
    dilig_count = (
        db.query(func.count(Diligencia.id))
        .filter(Diligencia.acao_id == a.id_acao)
        .scalar()
    )
    cert = a.certificacao
    return AcaoOut(
        id_acao=a.id_acao,
        id_certificacao=a.id_certificacao,
        id_requisito=a.id_requisito,
        id_item=a.id_item,
        id_unidade=a.id_unidade,
        nome=a.nome,
        descricao=a.descricao,
        prazo=a.prazo,
        data_envio=a.data_envio,
        status=a.status,
        data_aprovacao=a.data_aprovacao,
        criado_em=a.criado_em,
        atualizado_em=a.atualizado_em,
        cod_requisito=a.requisito.cod_requisito if a.requisito else "",
        nome_requisito=a.requisito.nome_requisito if a.requisito else "",
        nome_item=a.item.nome_item if a.item else "",
        sigla_unidade=a.unidade.sigla if a.unidade else "",
        nome_unidade=a.unidade.nome if a.unidade else "",
        nome_certificacao=cert.nome_certificacao if cert else "",
        nome_nivel=cert.nivel.nome_nivel if cert and cert.nivel else "",
        versao_manual=cert.manual.versao_manual if cert and cert.manual else "",
        historico=[
            {"dt": h.data_evento.strftime("%d/%m"), "ev": h.descricao_evento}
            for h in hist
        ],
        documentos=[
            {
                "id": d.id,
                "nome_arquivo": d.nome_arquivo,
                "tipo_arquivo": d.tipo_arquivo,
                "versao": d.versao,
                "tamanho_bytes": d.tamanho_bytes,
                "enviado_em": d.enviado_em,
            }
            for d in sorted(a.documentos, key=lambda doc: doc.enviado_em or datetime.min)
        ],
        diligencias_count=dilig_count or 0,
    )


def _buscar(db: Session, id_acao: int, tenant_id: str) -> Acao:
    acao = (
        db.query(Acao)
        .filter(Acao.id_acao == id_acao, Acao.tenant_id == tenant_id)
        .first()
    )
    if not acao:
        raise HTTPException(status_code=404, detail="Ação não encontrada")
    return acao


def _resolver_certificacao(
    db: Session, tenant_id: str, requisito: Requisito, item: Item | None
) -> Certificacao:
    """Certificação do ente: manual do requisito no nível do item."""
    if item is not None:
        cert = (
            db.query(Certificacao)
            .join(Nivel, Nivel.id_nivel == Certificacao.id_nivel)
            .filter(
                Certificacao.tenant_id == tenant_id,
                Certificacao.id_manual == requisito.id_manual,
                Nivel.nome_nivel == item.nivel,
            )
            .first()
        )
        if cert:
            return cert
    cert = (
        db.query(Certificacao)
        .join(Nivel, Nivel.id_nivel == Certificacao.id_nivel)
        .filter(
            Certificacao.tenant_id == tenant_id,
            Certificacao.id_manual == requisito.id_manual,
        )
        .order_by(Nivel.nome_nivel)
        .first()
    )
    if cert:
        return cert
    raise HTTPException(
        status_code=422,
        detail="Certificação não encontrada para o manual do requisito",
    )


def _validar_relacoes(
    db: Session,
    *,
    tenant_id: str,
    id_requisito: int,
    id_item: int,
    id_unidade: str,
) -> tuple[Requisito, Item, Unidade]:
    requisito = db.get(Requisito, id_requisito)
    if not requisito:
        raise HTTPException(status_code=422, detail="Requisito não encontrado")
    item = db.get(Item, id_item)
    if not item:
        raise HTTPException(status_code=422, detail="Item não encontrado")
    if item.id_requisito != id_requisito:
        raise HTTPException(
            status_code=422, detail="O item informado não pertence ao requisito"
        )
    unidade = db.get(Unidade, id_unidade)
    if not unidade:
        raise HTTPException(status_code=422, detail="Unidade não encontrada")
    return requisito, item, unidade


@router.get("", response_model=list[AcaoOut])
def listar_acoes(
    status: str | None = Query(None),
    dimensao: str | None = Query(None),
    id_unidade: str | None = Query(None),
    id_requisito: int | None = Query(None),
    id_certificacao: int | None = Query(None),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    q = db.query(Acao).filter(Acao.tenant_id == usuario.tenant_id)

    perfis = nomes_perfis(db, usuario)
    if "Operador" in perfis and not perfis.intersection(_PERFIS_ADMIN):
        unidades = _unidades_do_usuario(db, usuario)
        if unidades:
            q = q.filter(Acao.id_unidade.in_(unidades))

    if status:
        q = q.filter(Acao.status == status)
    if id_unidade:
        q = q.filter(Acao.id_unidade == id_unidade)
    if id_requisito:
        q = q.filter(Acao.id_requisito == id_requisito)
    if id_certificacao:
        q = q.filter(Acao.id_certificacao == id_certificacao)
    if dimensao:
        prefixo = _PREFIXO_DIMENSAO.get(dimensao, "")
        if prefixo:
            q = q.join(Requisito, Requisito.id_requisito == Acao.id_requisito).filter(
                Requisito.cod_requisito.like(f"{prefixo}%")
            )

    acoes = (
        q.options(
            joinedload(Acao.requisito),
            joinedload(Acao.unidade),
            joinedload(Acao.item),
            joinedload(Acao.certificacao).joinedload(Certificacao.nivel),
            joinedload(Acao.certificacao).joinedload(Certificacao.manual),
        )
        .order_by(Acao.prazo, Acao.id_acao)
        .all()
    )
    return [_montar_out(db, a) for a in acoes]


@router.post("/{id_acao}/documentos", status_code=201)
def enviar_documento_acao(
    id_acao: int,
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    perfis = nomes_perfis(db, usuario)
    if "Operador" not in perfis:
        raise HTTPException(status_code=403, detail="Apenas o Operacional pode enviar comprovações")

    acao = _buscar(db, id_acao, usuario.tenant_id)
    unidades = _unidades_do_usuario(db, usuario)
    if acao.id_unidade not in unidades:
        raise HTTPException(status_code=403, detail="Ação fora das suas unidades")
    if acao.status not in {"PENDENTE", "DILIGÊNCIA"}:
        raise HTTPException(status_code=409, detail="A ação não está aguardando uma comprovação")

    nome_original = (arquivo.filename or "").replace("\\", "/").rsplit("/", 1)[-1].strip()
    extensao = Path(nome_original).suffix.lower()
    if not nome_original or extensao not in _EXTENSOES_DOCUMENTO:
        raise HTTPException(status_code=422, detail="Envie um arquivo PDF, DOCX ou XLSX")

    conteudo = arquivo.file.read(_MAX_DOCUMENTO_BYTES + 1)
    if len(conteudo) > _MAX_DOCUMENTO_BYTES:
        raise HTTPException(status_code=413, detail="O arquivo deve ter no máximo 20 MB")
    if not conteudo:
        raise HTTPException(status_code=422, detail="O arquivo está vazio")

    documentos_anteriores = (
        db.query(Documento)
        .filter(Documento.acao_id == acao.id_acao)
        .count()
    )
    nome_storage = f"{uuid4().hex}{extensao}"
    raiz_storage = get_settings().upload_dir.resolve()
    caminho = raiz_storage / usuario.tenant_id / str(acao.id_acao) / nome_storage
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_bytes(conteudo)

    documento = Documento(
        acao_id=acao.id_acao,
        nome_arquivo=nome_original[:300],
        tipo_arquivo=extensao.lstrip("."),
        versao=documentos_anteriores + 1,
        tamanho_bytes=len(conteudo),
        caminho_storage=str(caminho.relative_to(raiz_storage)),
        enviado_por=usuario.id,
    )
    db.add(documento)
    acao.status = "ENVIADO"
    acao.data_envio = date.today()
    db.add(
        HistoricoAcao(
            acao_id=acao.id_acao,
            descricao_evento=f"Comprovação enviada: {nome_original[:200]} por {usuario.nome_completo}",
            usuario_id=usuario.id,
        )
    )
    try:
        db.commit()
        db.refresh(documento)
    except SQLAlchemyError:
        db.rollback()
        caminho.unlink(missing_ok=True)
        raise

    return {
        "id": documento.id,
        "nome_arquivo": documento.nome_arquivo,
        "tipo_arquivo": documento.tipo_arquivo,
        "versao": documento.versao,
        "tamanho_bytes": documento.tamanho_bytes,
        "enviado_em": documento.enviado_em,
    }


@router.get("/{id_acao}/documentos/{id_documento}")
def baixar_documento_acao(
    id_acao: int,
    id_documento: str,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    acao = _buscar(db, id_acao, usuario.tenant_id)
    perfis = nomes_perfis(db, usuario)
    if "Operador" in perfis and not perfis.intersection(_PERFIS_ADMIN):
        if acao.id_unidade not in _unidades_do_usuario(db, usuario):
            raise HTTPException(status_code=403, detail="Ação fora das suas unidades")

    documento = (
        db.query(Documento)
        .filter(Documento.id == id_documento, Documento.acao_id == id_acao)
        .first()
    )
    if not documento:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    raiz_storage = get_settings().upload_dir.resolve()
    caminho = (raiz_storage / documento.caminho_storage).resolve()
    if not caminho.is_relative_to(raiz_storage) or not caminho.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado no armazenamento")

    tipos = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
    return FileResponse(
        caminho,
        media_type=tipos.get(documento.tipo_arquivo, "application/octet-stream"),
        filename=documento.nome_arquivo,
    )


@router.get("/{id_acao}", response_model=AcaoOut)
def obter_acao(
    id_acao: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    return _montar_out(db, _buscar(db, id_acao, usuario.tenant_id))


@router.post("", response_model=list[AcaoOut], status_code=201)
def criar_acoes(
    req: AcaoCreate,
    db: Session = Depends(get_db),
    atual: Usuario = Depends(_admin),
):
    """Cria uma ação por unidade informada (multi-setor)."""
    alvos = req.unidade_ids or ([req.id_unidade] if req.id_unidade else [])
    if not alvos:
        raise HTTPException(status_code=422, detail="Informe ao menos uma unidade")
    if req.status != "PENDENTE":
        raise HTTPException(
            status_code=422,
            detail="Novas ações devem iniciar com status PENDENTE",
        )

    criado: list[Acao] = []
    for uid in alvos:
        requisito, item, _ = _validar_relacoes(
            db,
            tenant_id=atual.tenant_id,
            id_requisito=req.id_requisito,
            id_item=req.id_item,
            id_unidade=uid,
        )
        if req.id_certificacao is not None:
            cert = db.get(Certificacao, req.id_certificacao)
            if not cert or cert.tenant_id != atual.tenant_id:
                raise HTTPException(status_code=422, detail="Certificação não encontrada")
        else:
            cert = _resolver_certificacao(db, atual.tenant_id, requisito, item)

        acao = Acao(
            tenant_id=atual.tenant_id,
            id_certificacao=cert.id_certificacao,
            id_requisito=req.id_requisito,
            id_item=req.id_item,
            id_unidade=uid,
            nome=req.nome,
            descricao=req.descricao,
            prazo=req.prazo,
            data_envio=None,
            status="PENDENTE",
            criado_por=atual.id,
        )
        db.add(acao)
        db.flush()
        db.add(
            HistoricoAcao(
                acao_id=acao.id_acao,
                descricao_evento=f"Ação criada por {atual.nome_completo}",
                usuario_id=atual.id,
            )
        )
        criado.append(acao)

    db.commit()
    return [_montar_out(db, a) for a in criado]


@router.put("/{id_acao}", response_model=AcaoOut)
def atualizar_acao(
    id_acao: int,
    req: AcaoUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    acao = _buscar(db, id_acao, usuario.tenant_id)
    perfis = nomes_perfis(db, usuario)
    if not perfis.intersection(_PERFIS_ADMIN):
        raise HTTPException(
            status_code=403,
            detail="Acesso negado. Perfil necessário: Admin Master, Admin do Ente",
        )

    dados = req.model_dump(exclude_unset=True)
    if "status" in dados:
        raise HTTPException(
            status_code=409,
            detail="Altere o status pela operação específica de revisão ou envio",
        )

    id_requisito = dados.get("id_requisito", acao.id_requisito)
    id_item = dados.get("id_item", acao.id_item)
    id_unidade = dados.get("id_unidade", acao.id_unidade)
    if id_item is None:
        raise HTTPException(status_code=422, detail="Informe o item da ação")
    requisito, item, _ = _validar_relacoes(
        db,
        tenant_id=usuario.tenant_id,
        id_requisito=id_requisito,
        id_item=id_item,
        id_unidade=id_unidade,
    )
    if "id_certificacao" in dados:
        cert = db.get(Certificacao, dados["id_certificacao"])
        if not cert or cert.tenant_id != usuario.tenant_id:
            raise HTTPException(status_code=422, detail="Certificação não encontrada")
    else:
        dados["id_certificacao"] = _resolver_certificacao(
            db, usuario.tenant_id, requisito, item
        ).id_certificacao

    for campo, valor in dados.items():
        setattr(acao, campo, valor)
    if acao.status == "ENVIADO" and not acao.data_envio:
        acao.data_envio = date.today()
    if acao.status == "APROVADO" and not acao.data_aprovacao:
        acao.data_aprovacao = date.today()

    db.commit()
    db.refresh(acao)
    return _montar_out(db, acao)


@router.patch("/{id_acao}/status", response_model=AcaoOut)
def atualizar_status(
    id_acao: int,
    req: AcaoStatusUpdate,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    acao = _buscar(db, id_acao, usuario.tenant_id)
    if req.status not in _STATUS_VALIDOS:
        raise HTTPException(
            status_code=422,
            detail="Status deve ser PENDENTE, ENVIADO, APROVADO ou DILIGÊNCIA",
        )

    perfis = nomes_perfis(db, usuario)
    if req.status == "ENVIADO":
        raise HTTPException(
            status_code=409,
            detail="Envie o documento da comprovação para alterar o status da ação",
        )
    if not perfis.intersection(_PERFIS_ADMIN):
        raise HTTPException(status_code=403, detail="Apenas Admin pode revisar o status da ação")
    if req.status == "APROVADO" and acao.status != "ENVIADO":
        raise HTTPException(status_code=409, detail="A ação precisa estar enviada para ser aprovada")
    if req.status == "DILIGÊNCIA":
        raise HTTPException(
            status_code=409,
            detail="Emita uma diligência para alterar o status da ação",
        )
    if req.status == "PENDENTE":
        raise HTTPException(
            status_code=409,
            detail="O status PENDENTE só pode ser definido na criação da ação",
        )

    status_anterior = acao.status
    acao.status = req.status
    if req.status == "ENVIADO" and not acao.data_envio:
        acao.data_envio = date.today()
    if req.status == "APROVADO":
        acao.data_aprovacao = date.today()

    db.add(
        HistoricoAcao(
            acao_id=acao.id_acao,
            descricao_evento=(
                f"Status alterado: {status_anterior} → {req.status} "
                f"por {usuario.nome_completo}"
            ),
            usuario_id=usuario.id,
        )
    )
    db.commit()
    db.refresh(acao)
    return _montar_out(db, acao)


@router.delete("/{id_acao}", status_code=204)
def remover_acao(
    id_acao: int,
    db: Session = Depends(get_db),
    usuario: Usuario = Depends(get_usuario_atual),
):
    acao = _buscar(db, id_acao, usuario.tenant_id)
    perfis = nomes_perfis(db, usuario)
    if not perfis.intersection(_PERFIS_ADMIN):
        raise HTTPException(
            status_code=403,
            detail="Acesso negado. Perfil necessário: Admin Master, Admin do Ente",
        )
    db.delete(acao)
    db.commit()
