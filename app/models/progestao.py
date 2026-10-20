"""Pró-Gestão: manual/dimensões/requisitos/itens, plano de ação e diligências."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.base import Base, gen_uuid


class Manual(Base):
    """Manual do Pró-Gestão RPPS — um registro por versão publicada."""

    __tablename__ = "manual"

    id_manual = Column(Integer, primary_key=True)
    nome_manual = Column(String(200), nullable=False)
    versao_manual = Column(String(20), nullable=False, unique=True)

    requisitos = relationship("Requisito", back_populates="manual")


class Dimensao(Base):
    """Dimensões do manual (Controles Internos, Governança, Educação Previdenciária)."""

    __tablename__ = "dimensao"

    id_dimensao = Column(Integer, primary_key=True)
    nome_dimensao = Column(String(150), nullable=False, unique=True)

    requisitos = relationship("Requisito", back_populates="dimensao")


class Requisito(Base):
    """Requisito do manual, ligado a uma versão e a uma dimensão."""

    __tablename__ = "requisito"
    __table_args__ = (
        UniqueConstraint("id_manual", "cod_requisito", name="uq_requisito_manual_cod"),
    )

    id_requisito = Column(Integer, primary_key=True)
    id_manual = Column(
        Integer, ForeignKey("manual.id_manual", ondelete="RESTRICT"), nullable=False
    )
    id_dimensao = Column(
        Integer, ForeignKey("dimensao.id_dimensao", ondelete="RESTRICT"), nullable=False
    )
    cod_requisito = Column(String(10), nullable=False)
    nome_requisito = Column(String(200), nullable=False)

    manual = relationship("Manual", back_populates="requisitos")
    dimensao = relationship("Dimensao", back_populates="requisitos")
    itens = relationship("Item", back_populates="requisito", cascade="all, delete-orphan")
    acoes = relationship("Acao", back_populates="requisito")
    unidades_vinc = relationship("RequisitoUnidade", back_populates="requisito")


class Item(Base):
    """Item exigido por requisito em cada nível de certificação (I–IV)."""

    __tablename__ = "item"
    __table_args__ = (
        UniqueConstraint(
            "id_requisito", "nivel", "nome_item", name="uq_item_req_nivel_nome"
        ),
    )

    id_item = Column(Integer, primary_key=True)
    id_requisito = Column(
        Integer, ForeignKey("requisito.id_requisito", ondelete="CASCADE"), nullable=False
    )
    nome_item = Column(String(300), nullable=False)
    nivel = Column(String(3), nullable=False)  # I | II | III | IV
    descricao = Column(Text)

    requisito = relationship("Requisito", back_populates="itens")


class RequisitoUnidade(Base):
    __tablename__ = "requisito_unidade"

    requisito_id = Column(
        Integer, ForeignKey("requisito.id_requisito"), primary_key=True
    )
    unidade_id = Column(String(36), ForeignKey("unidades.id"), primary_key=True)

    requisito = relationship("Requisito", back_populates="unidades_vinc")
    unidade = relationship("Unidade", back_populates="req_vinculos")


class Acao(Base):
    __tablename__ = "acoes"

    id_acao = Column(String(10), primary_key=True)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    requisito_id = Column(
        Integer, ForeignKey("requisito.id_requisito"), nullable=False
    )
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
