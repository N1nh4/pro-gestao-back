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
    id_requisito: int | None = None
    requisito_cod: str | None = None  # legado; usado quando id_requisito não é informado
    item: str
    descricao_acao: str
    prazo: date
    unidade_ids: list[str] = Field(default_factory=list)
    unidade_id: str | None = None


class AcaoStatusUpdate(BaseModel):
    status: str  # PENDENTE | ENVIADO | APROVADO | DILIGÊNCIA


class AcaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_acao: str
    requisito_id: int
    item: str
    descricao_acao: str
    unidade_id: str
    status: str
    prazo: date | None
    dt_envio: date | None
    dt_aprovacao: date | None
    criado_em: datetime | None


class DiligenciaCreate(BaseModel):
    acao_id: str
    situacao_detectada: str
    criticidade: str = "media"
    prazo_resposta: date


class DiligenciaRetorno(BaseModel):
    retorno_texto: str


class DiligenciaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    num: str
    acao_id: str
    situacao_detectada: str
    criticidade: str
    prazo_resposta: date | None
    status: str
    emitido_em: datetime | None
    retorno_texto: str | None
    retorno_em: datetime | None
