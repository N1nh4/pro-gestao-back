from datetime import date

from pydantic import BaseModel, ConfigDict


class TarefaCreate(BaseModel):
    titulo: str
    descricao: str | None = None
    prioridade: str = "media"
    status: str = "pendente"
    prazo: date | None = None
    acao_id: str | None = None
    unidade_id: str | None = None
    responsavel_id: str | None = None


class TarefaStatusUpdate(BaseModel):
    status: str


class EvidenciaCreate(BaseModel):
    titulo: str
    tipo: str = "outro"
    id_requisito: int | None = None
    requisito_cod: str | None = None  # legado; usado quando id_requisito não é informado
    acao_id: str | None = None
    observacoes: str | None = None


class ProcessoCreate(BaseModel):
    nivel_pretendido: str
    tipo_processo: str = "inicial"
    entidade_certificadora: str | None = None
    numero_protocolo: str | None = None
    data_adesao: date
    data_inicio_avaliacao: date | None = None
    data_prevista_auditoria: date | None = None
    observacoes: str | None = None


class ProcessoStatusUpdate(BaseModel):
    status: str | None = None
    nivel_certificado: str | None = None
    observacoes: str | None = None


class ProcessoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    nivel_pretendido: str
    tipo_processo: str
    entidade_certificadora: str | None
    numero_protocolo: str | None
    status: str
    nivel_certificado: str | None
    dados_confirmados: bool
