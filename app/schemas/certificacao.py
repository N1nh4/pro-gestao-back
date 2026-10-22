from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class NivelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_nivel: int
    nome_nivel: str


class NivelCreate(BaseModel):
    nome_nivel: str = Field(min_length=1, max_length=10)


class NivelUpdate(BaseModel):
    nome_nivel: str | None = Field(default=None, min_length=1, max_length=10)


class CertificacaoCreate(BaseModel):
    nome_certificacao: str = Field(min_length=1, max_length=200)
    status: str = "PENDENTE"
    numero_certificado: str | None = None
    data_certificacao: date | None = None
    data_validade: date | None = None
    entidade_certificadora: str | None = None


class CertificacaoUpdate(BaseModel):
    nome_certificacao: str | None = Field(default=None, min_length=1, max_length=200)
    status: str | None = None
    numero_certificado: str | None = None
    data_certificacao: date | None = None
    data_validade: date | None = None
    entidade_certificadora: str | None = None


class CertificacaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_certificacao: int
    nome_certificacao: str
    status: str
    numero_certificado: str | None
    data_certificacao: date | None
    data_validade: date | None
    entidade_certificadora: str | None
    criado_em: datetime | None
    atualizado_em: datetime | None
    auditorias_count: int = 0
    acoes_count: int = 0


class AuditoriaCreate(BaseModel):
    id_certificacao: int
    id_manual: int
    tipo: str = "pre_auditoria"
    modalidade: str = "presencial"
    data_auditoria: date
    duracao_horas: float | None = None
    nivel_recomendado: str | None = None
    parecer_geral: str | None = None
    conclusao: str = "pendente"
    auditor_nome: str | None = None
    auditor_email: EmailStr | None = None


class AuditoriaUpdate(BaseModel):
    id_certificacao: int | None = None
    id_manual: int | None = None
    tipo: str | None = None
    modalidade: str | None = None
    data_auditoria: date | None = None
    duracao_horas: float | None = None
    nivel_recomendado: str | None = None
    parecer_geral: str | None = None
    conclusao: str | None = None
    auditor_nome: str | None = None
    auditor_email: EmailStr | None = None


class AuditoriaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    id_certificacao: int
    id_manual: int
    tipo: str
    modalidade: str
    data_auditoria: date
    duracao_horas: float | None
    nivel_recomendado: str | None
    parecer_geral: str | None
    conclusao: str
    auditor_nome: str | None
    auditor_email: str | None
    criado_em: datetime | None
    atualizado_em: datetime | None
    nome_certificacao: str = ""
    nome_manual: str = ""
    versao_manual: str = ""
    acoes_count: int = 0
