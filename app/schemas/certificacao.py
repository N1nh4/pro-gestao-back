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
    id_manual: int
    id_nivel: int
    nome_certificacao: str = Field(min_length=1, max_length=200)
    status: str = "PENDENTE"
    numero_certificado: str | None = None
    data_certificacao: date | None = None
    data_validade: date | None = None
    entidade_certificadora: str | None = None


class CertificacaoUpdate(BaseModel):
    id_nivel: int | None = None
    nome_certificacao: str | None = Field(default=None, min_length=1, max_length=200)
    status: str | None = None
    numero_certificado: str | None = None
    data_certificacao: date | None = None
    data_validade: date | None = None
    entidade_certificadora: str | None = None


class CertificacaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_certificacao: int
    id_manual: int
    id_nivel: int
    nome_certificacao: str
    status: str
    numero_certificado: str | None
    data_certificacao: date | None
    data_validade: date | None
    entidade_certificadora: str | None
    criado_em: datetime | None
    atualizado_em: datetime | None
    nome_nivel: str = ""
    nome_manual: str = ""
    versao_manual: str = ""


class AuditoriaCreate(BaseModel):
    tipo: str = "pre_auditoria"
    modalidade: str = "presencial"
    data_auditoria: date
    duracao_horas: float | None = None
    nivel_auditado: str | None = None
    nivel_recomendado: str | None = None
    parecer_geral: str | None = None
    conclusao: str = "pendente"
    auditor_nome: str | None = None
    auditor_email: EmailStr | None = None


class AuditoriaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tipo: str
    modalidade: str
    data_auditoria: date
    duracao_horas: float | None
    nivel_auditado: str | None
    nivel_recomendado: str | None
    parecer_geral: str | None
    conclusao: str
    auditor_nome: str | None
