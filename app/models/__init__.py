"""Modelos SQLAlchemy (importados aqui para registrar no metadata da Base)."""

from app.models.certificacao import Auditoria, Certificacao, ProcessoProgestao
from app.models.ged import Evidencia, Tarefa
from app.models.progestao import (
    Acao,
    Diligencia,
    Documento,
    HistoricoAcao,
    HistoricoDiligencia,
    MensagemDiligencia,
    PrazoExtensao,
    Requisito,
    RequisitoUnidade,
)
from app.models.rbac import (
    Pagina,
    Perfil,
    PerfilPagina,
    SessaoPerfil,
    Tenant,
    Unidade,
    Usuario,
    UsuarioUnidadePerfil,
)

__all__ = [
    # rbac
    "Tenant",
    "Usuario",
    "Perfil",
    "SessaoPerfil",
    "Pagina",
    "PerfilPagina",
    "Unidade",
    "UsuarioUnidadePerfil",
    # progestão
    "Requisito",
    "RequisitoUnidade",
    "Acao",
    "HistoricoAcao",
    "Diligencia",
    "PrazoExtensao",
    "HistoricoDiligencia",
    "MensagemDiligencia",
    "Documento",
    # certificação
    "Certificacao",
    "ProcessoProgestao",
    "Auditoria",
    # operacional
    "Tarefa",
    "Evidencia",
]
