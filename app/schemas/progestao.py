from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class RequisitoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cod: str
    dimensao: str
    titulo: str
    essencial: bool
    nivel_minimo: str | None


class AcaoCreate(BaseModel):
    id_auditoria: str
    id_requisito: int
    id_item: int
    id_unidade: str | None = None
    unidade_ids: list[str] = Field(default_factory=list)
    nome: str = Field(min_length=1, max_length=300)
    descricao: str = Field(min_length=1)
    prazo: date
    status: str = "PENDENTE"
    data_envio: date | None = None


class AcaoUpdate(BaseModel):
    id_auditoria: str | None = None
    id_requisito: int | None = None
    id_item: int | None = None
    id_unidade: str | None = None
    nome: str | None = Field(default=None, min_length=1, max_length=300)
    descricao: str | None = None
    prazo: date | None = None
    status: str | None = None
    data_envio: date | None = None
    data_aprovacao: date | None = None


class AcaoStatusUpdate(BaseModel):
    status: str  # PENDENTE | ENVIADO | APROVADO | DILIGÊNCIA


class AcaoHistoricoOut(BaseModel):
    dt: str
    ev: str


class AcaoDocumentoOut(BaseModel):
    id: str
    nome_arquivo: str
    tipo_arquivo: str
    versao: int | None
    tamanho_bytes: int | None
    enviado_em: datetime | None


class AcaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_acao: int
    id_auditoria: str
    id_requisito: int
    id_item: int | None
    id_unidade: str
    nome: str
    descricao: str
    prazo: date
    data_envio: date | None
    status: str
    data_aprovacao: date | None
    criado_em: datetime | None
    atualizado_em: datetime | None
    # nomes resolvidos por JOIN (leitura)
    cod_requisito: str = ""
    nome_requisito: str = ""
    nome_item: str = ""
    sigla_unidade: str = ""
    nome_unidade: str = ""
    nome_certificacao: str = ""
    nome_manual: str = ""
    versao_manual: str = ""
    nome_nivel: str = ""
    historico: list[AcaoHistoricoOut] = []
    documentos: list[AcaoDocumentoOut] = []
    diligencias_count: int = 0


class DiligenciaCreate(BaseModel):
    acao_id: int
    situacao_detectada: str
    criticidade: str = "media"
    prazo_resposta: date


class DiligenciaRetorno(BaseModel):
    retorno_texto: str


class DiligenciaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    num: str
    acao_id: int
    situacao_detectada: str
    criticidade: str
    prazo_resposta: date | None
    status: str
    emitido_em: datetime | None
    retorno_texto: str | None
    retorno_em: datetime | None
