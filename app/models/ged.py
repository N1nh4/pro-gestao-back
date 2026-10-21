"""Operacional: tarefas e evidências (GED)."""

from datetime import datetime

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)

from app.db.base import Base, gen_uuid


class Tarefa(Base):
    __tablename__ = "tarefas"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    titulo = Column(String(300), nullable=False)
    descricao = Column(Text)
    responsavel_id = Column(String(36), ForeignKey("usuarios.id"))
    unidade_id = Column(String(36), ForeignKey("unidades.id"))
    acao_id = Column(Integer)  # referência informacional à acao.id_acao
    prioridade = Column(String(10), default="media")  # baixa|media|alta|critica
    status = Column(String(20), default="pendente")  # pendente|em_andamento|concluida|cancelada
    prazo = Column(Date)
    concluida_em = Column(DateTime)
    criado_por = Column(String(36), ForeignKey("usuarios.id"))
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Evidencia(Base):
    __tablename__ = "evidencias"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    titulo = Column(String(300), nullable=False)
    tipo = Column(String(50))  # ata|relatorio|comprovante|politica|outro
    requisito_id = Column(Integer, ForeignKey("requisito.id_requisito"))
    acao_id = Column(Integer)  # referência informacional à acao.id_acao
    arquivo_nome = Column(String(300))
    arquivo_path = Column(String(500))
    arquivo_tamanho = Column(Integer)
    data_referencia = Column(Date)
    validade = Column(Date)
    observacoes = Column(Text)
    enviado_por = Column(String(36), ForeignKey("usuarios.id"))
    criado_em = Column(DateTime, default=datetime.utcnow)
