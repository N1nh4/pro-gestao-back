"""Certificação: certificados, processos Pró-Gestão e auditorias."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.db.base import Base, gen_uuid


class Certificacao(Base):
    __tablename__ = "certificacoes"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    nivel = Column(String(10), nullable=False)
    data_certificacao = Column(Date, nullable=False)
    data_validade = Column(Date, nullable=False)
    entidade_certificadora = Column(String(200), nullable=False)
    status = Column(String(20), default="vigente")
    numero_certificado = Column(String(50))
    observacoes = Column(Text)
    registrado_por = Column(String(36), ForeignKey("usuarios.id"))
    criado_em = Column(DateTime, default=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="certificacoes")


class ProcessoProgestao(Base):
    """Ciclo de certificação Pró-Gestão do ente."""

    __tablename__ = "processos_progestao"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    nivel_pretendido = Column(String(10), nullable=False)  # I|II|III|IV
    tipo_processo = Column(String(30), default="inicial")  # inicial|renovacao|mudanca_nivel|reanalise
    entidade_certificadora = Column(String(200))
    numero_protocolo = Column(String(60))
    data_adesao = Column(Date, nullable=False)
    data_inicio_avaliacao = Column(Date)
    data_prevista_auditoria = Column(Date)
    data_conclusao = Column(Date)
    status = Column(String(20), default="em_andamento")  # em_andamento|suspenso|concluido|cancelado
    nivel_certificado = Column(String(10))
    observacoes = Column(Text)
    dados_confirmados = Column(Boolean, default=False)
    dados_confirmados_em = Column(DateTime)
    dados_confirmados_por = Column(String(36), ForeignKey("usuarios.id"))
    criado_por = Column(String(36), ForeignKey("usuarios.id"))
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Auditoria(Base):
    __tablename__ = "auditorias"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    processo_id = Column(String(36), ForeignKey("processos_progestao.id"))
    tipo = Column(String(50), default="pre_auditoria")
    modalidade = Column(String(30), default="presencial")
    data_auditoria = Column(Date, nullable=False)
    duracao_horas = Column(Float)
    nivel_auditado = Column(String(10))
    nivel_recomendado = Column(String(10))
    parecer_geral = Column(Text)
    conclusao = Column(String(30), default="pendente")  # aprovado|reprovado|pendente|diligencia
    auditor_nome = Column(String(200))
    auditor_email = Column(String(200))
    criado_por = Column(String(36), ForeignKey("usuarios.id"))
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
