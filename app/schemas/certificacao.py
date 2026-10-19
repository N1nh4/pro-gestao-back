from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr


class CertificacaoCreate(BaseModel):
    nivel: str = "III"
    data_certificacao: date
    data_validade: date
    entidade_certificadora: str = ""
    status: str = "vigente"
    numero_certificado: str | None = None
    observacoes: str | None = None


class CertificacaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    nivel: str
    data_certificacao: date
    data_validade: date
    entidade_certificadora: str
    status: str
    numero_certificado: str | None
    observacoes: str | None


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
