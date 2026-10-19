"""Pró-Gestão: requisitos, plano de ação, diligências e documentos."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.db.base import Base, gen_uuid


class Requisito(Base):
    __tablename__ = "requisitos"

    cod = Column(String(10), primary_key=True)
    dimensao = Column(String(5), nullable=False)  # CI | GC | EP
    titulo = Column(String(200), nullable=False)
    descricao_nivel_i = Column(Text)
    descricao_nivel_ii = Column(Text)
    descricao_nivel_iii = Column(Text)
    descricao_nivel_iv = Column(Text)
    essencial = Column(Boolean, default=False)
    documentos_exigidos = Column(Text)
    nivel_minimo = Column(String(5))

    acoes = relationship("Acao", back_populates="requisito")
    unidades_vinc = relationship("RequisitoUnidade", back_populates="requisito")


class RequisitoUnidade(Base):
    __tablename__ = "requisito_unidade"

    requisito_cod = Column(String(10), ForeignKey("requisitos.cod"), primary_key=True)
    unidade_id = Column(String(36), ForeignKey("unidades.id"), primary_key=True)

    requisito = relationship("Requisito", back_populates="unidades_vinc")
    unidade = relationship("Unidade", back_populates="req_vinculos")


class Acao(Base):
    __tablename__ = "acoes"

    id_acao = Column(String(10), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    requisito_cod = Column(String(10), ForeignKey("requisitos.cod"), nullable=False)
    item = Column(String(200), nullable=False)
    descricao_acao = Column(Text, nullable=False)
    unidade_id = Column(String(36), ForeignKey("unidades.id"), nullable=False)
    status = Column(String(20), default="PENDENTE")  # PENDENTE|ENVIADO|APROVADO|DILIGÊNCIA
    prazo = Column(Date, nullable=False)
    dt_envio = Column(Date)
    dt_aprovacao = Column(Date)
    observacao = Column(Text)
    criado_por = Column(String(36), ForeignKey("usuarios.id"))
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="acoes")
    requisito = relationship("Requisito", back_populates="acoes")
    unidade = relationship("Unidade", back_populates="acoes")
    criado_por_usuario = relationship(
        "Usuario", back_populates="acoes_criadas", foreign_keys=[criado_por]
    )
    historico = relationship("HistoricoAcao", back_populates="acao", cascade="all, delete-orphan")
    diligencias = relationship("Diligencia", back_populates="acao", cascade="all, delete-orphan")
    documentos = relationship("Documento", back_populates="acao", cascade="all, delete-orphan")


class HistoricoAcao(Base):
    __tablename__ = "historico_acoes"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    acao_id = Column(String(10), ForeignKey("acoes.id_acao"), nullable=False)
    descricao_evento = Column(Text, nullable=False)
    usuario_id = Column(String(36), ForeignKey("usuarios.id"))
    data_evento = Column(DateTime, default=datetime.utcnow)

    acao = relationship("Acao", back_populates="historico")


class Diligencia(Base):
    __tablename__ = "diligencias"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    num = Column(String(10), nullable=False)
    acao_id = Column(String(10), ForeignKey("acoes.id_acao"), nullable=False)
    situacao_detectada = Column(Text, nullable=False)
    criticidade = Column(String(10), default="media")
    prazo_resposta = Column(Date, nullable=False)
    prazo_original = Column(Date, nullable=False)
    status = Column(String(20), default="aberta")
    emitido_por = Column(String(36), ForeignKey("usuarios.id"), nullable=False)
    emitido_em = Column(DateTime, default=datetime.utcnow)
    retorno_texto = Column(Text)
    retorno_em = Column(DateTime)

    acao = relationship("Acao", back_populates="diligencias")
    emitido_por_usuario = relationship("Usuario", back_populates="diligencias_emitidas")
    prazo_extensoes = relationship(
        "PrazoExtensao", back_populates="diligencia", cascade="all, delete-orphan"
    )
    historico = relationship(
        "HistoricoDiligencia", back_populates="diligencia", cascade="all, delete-orphan"
    )
    mensagens = relationship(
        "MensagemDiligencia", back_populates="diligencia", cascade="all, delete-orphan"
    )
    documentos = relationship("Documento", back_populates="diligencia")


class PrazoExtensao(Base):
    __tablename__ = "prazo_extensoes"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    diligencia_id = Column(String(36), ForeignKey("diligencias.id"), nullable=False)
    prazo_anterior = Column(Date, nullable=False)
    prazo_novo = Column(Date, nullable=False)
    motivo = Column(Text, nullable=False)
    concedido_por = Column(String(36), ForeignKey("usuarios.id"), nullable=False)
    concedido_em = Column(DateTime, default=datetime.utcnow)

    diligencia = relationship("Diligencia", back_populates="prazo_extensoes")


class HistoricoDiligencia(Base):
    __tablename__ = "historico_diligencias"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    diligencia_id = Column(String(36), ForeignKey("diligencias.id"), nullable=False)
    descricao_evento = Column(Text, nullable=False)
    usuario_id = Column(String(36), ForeignKey("usuarios.id"))
    data_evento = Column(DateTime, default=datetime.utcnow)

    diligencia = relationship("Diligencia", back_populates="historico")


class MensagemDiligencia(Base):
    __tablename__ = "mensagens_diligencia"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    diligencia_id = Column(String(36), ForeignKey("diligencias.id"), nullable=False)
    tipo = Column(String(5), nullable=False)  # in | out
    remetente = Column(String(200), nullable=False)
    mensagem = Column(Text, nullable=False)
    enviado_em = Column(DateTime, default=datetime.utcnow)

    diligencia = relationship("Diligencia", back_populates="mensagens")


class Documento(Base):
    __tablename__ = "documentos"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    acao_id = Column(String(10), ForeignKey("acoes.id_acao"), nullable=False)
    diligencia_id = Column(String(36), ForeignKey("diligencias.id"))
    nome_arquivo = Column(String(300), nullable=False)
    tipo_arquivo = Column(String(10), nullable=False)
    versao = Column(Integer, default=1)
    tamanho_bytes = Column(BigInteger)
    caminho_storage = Column(Text)
    enviado_por = Column(String(36), ForeignKey("usuarios.id"), nullable=False)
    enviado_em = Column(DateTime, default=datetime.utcnow)

    acao = relationship("Acao", back_populates="documentos")
    diligencia = relationship("Diligencia", back_populates="documentos")
    enviado_por_usuario = relationship("Usuario", back_populates="documentos_enviados")
