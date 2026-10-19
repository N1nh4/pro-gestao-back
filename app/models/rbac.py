"""RBAC / tenancy: Tenant, Usuario, Perfil, Pagina, Unidade e vínculos."""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.base import Base, gen_uuid


class Tenant(Base):
    """Ente federativo / RPPS atendido pelo sistema."""

    __tablename__ = "tenants"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    nome_ente = Column(String(200), nullable=False)
    cnpj_ente = Column(String(18), nullable=False, unique=True)
    uf = Column(String(2), nullable=False)
    tipo_ente = Column(String(50), nullable=False, default="Município")
    nome_ug = Column(String(200))
    cnpj_ug = Column(String(18))
    nivel_atual = Column(String(10))
    nivel_pretendido = Column(String(10))
    data_adesao = Column(Date)
    entidade_certificadora = Column(String(200))
    num_segurados = Column(Integer)
    email_contato = Column(String(200))
    telefone_contato = Column(String(20))
    observacoes = Column(Text)
    ativo = Column(Boolean, default=True)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    usuarios = relationship("Usuario", back_populates="tenant", foreign_keys="Usuario.tenant_id")
    perfis = relationship("Perfil", back_populates="tenant")
    unidades = relationship("Unidade", back_populates="tenant")
    acoes = relationship("Acao", back_populates="tenant")
    certificacoes = relationship("Certificacao", back_populates="tenant")


class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = (
        UniqueConstraint("tenant_id", "login", name="uq_login_por_ente"),
        UniqueConstraint("tenant_id", "email", name="uq_email_por_ente"),
        UniqueConstraint("tenant_id", "id_usuario", name="uq_seq_por_ente"),
    )

    id = Column(String(36), primary_key=True, default=gen_uuid)
    id_usuario = Column(String(10), nullable=False)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    login = Column(String(100), nullable=False)
    email = Column(String(200), nullable=False)
    nome_completo = Column(String(200), nullable=False)
    senha_hash = Column(Text, nullable=False)
    status = Column(String(20), default="ativo")
    ultimo_acesso = Column(DateTime)
    tentativas_falhas = Column(SmallInteger, default=0)
    bloqueado_ate = Column(DateTime)
    criado_por = Column(String(36), ForeignKey("usuarios.id"))
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="usuarios", foreign_keys=[tenant_id])
    sessoes = relationship("SessaoPerfil", back_populates="usuario")
    acoes_criadas = relationship(
        "Acao", back_populates="criado_por_usuario", foreign_keys="Acao.criado_por"
    )
    diligencias_emitidas = relationship("Diligencia", back_populates="emitido_por_usuario")
    documentos_enviados = relationship("Documento", back_populates="enviado_por_usuario")
    vinculos = relationship(
        "UsuarioUnidadePerfil",
        back_populates="usuario",
        foreign_keys="UsuarioUnidadePerfil.usuario_id",
    )


class Perfil(Base):
    __tablename__ = "perfis"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"))
    nome = Column(String(80), nullable=False)
    descricao = Column(Text)
    tipo = Column(String(20), default="customizado")  # nativo | customizado
    requer_setor = Column(Boolean, default=True)
    ativo = Column(Boolean, default=True)
    criado_por = Column(String(36), ForeignKey("usuarios.id"))
    criado_em = Column(DateTime, default=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="perfis")
    permissoes = relationship("PerfilPagina", back_populates="perfil")
    sessoes = relationship("SessaoPerfil", back_populates="perfil")
    vinculos = relationship("UsuarioUnidadePerfil", back_populates="perfil")


class SessaoPerfil(Base):
    __tablename__ = "sessoes_perfil"

    jti = Column(String(36), primary_key=True)
    usuario_id = Column(String(36), ForeignKey("usuarios.id"), nullable=False)
    perfil_id = Column(String(36), ForeignKey("perfis.id"), nullable=False)
    iniciado_em = Column(DateTime, default=datetime.utcnow)
    expira_em = Column(DateTime, nullable=False)

    usuario = relationship("Usuario", back_populates="sessoes")
    perfil = relationship("Perfil", back_populates="sessoes")


class Pagina(Base):
    __tablename__ = "paginas"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    nome = Column(String(100), nullable=False)
    rota = Column(String(100), nullable=False, unique=True)
    descricao = Column(Text)
    icone = Column(String(60))
    ordem = Column(SmallInteger, default=0)
    ativo = Column(Boolean, default=True)

    permissoes = relationship("PerfilPagina", back_populates="pagina")


class PerfilPagina(Base):
    __tablename__ = "perfil_paginas"

    perfil_id = Column(String(36), ForeignKey("perfis.id"), primary_key=True)
    pagina_id = Column(String(36), ForeignKey("paginas.id"), primary_key=True)
    pode_visualizar = Column(Boolean, default=False)
    pode_criar = Column(Boolean, default=False)
    pode_editar = Column(Boolean, default=False)
    pode_aprovar = Column(Boolean, default=False)
    pode_excluir = Column(Boolean, default=False)
    pode_exportar = Column(Boolean, default=False)
    atualizado_por = Column(String(36), ForeignKey("usuarios.id"))
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    perfil = relationship("Perfil", back_populates="permissoes")
    pagina = relationship("Pagina", back_populates="permissoes")


class Unidade(Base):
    __tablename__ = "unidades"
    __table_args__ = (UniqueConstraint("tenant_id", "sigla", name="uq_sigla_por_ente"),)

    id = Column(String(36), primary_key=True, default=gen_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    sigla = Column(String(20), nullable=False)
    nome = Column(String(150), nullable=False)
    descricao = Column(Text)
    ativo = Column(Boolean, default=True)
    criado_por = Column(String(36), ForeignKey("usuarios.id"))
    criado_em = Column(DateTime, default=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="unidades")
    vinculos = relationship("UsuarioUnidadePerfil", back_populates="unidade")
    req_vinculos = relationship("RequisitoUnidade", back_populates="unidade")
    acoes = relationship("Acao", back_populates="unidade")


class UsuarioUnidadePerfil(Base):
    """Junção tripla: concede um perfil (e opcionalmente uma unidade) ao usuário."""

    __tablename__ = "usuario_unidade_perfil"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    usuario_id = Column(String(36), ForeignKey("usuarios.id"), nullable=False)
    unidade_id = Column(String(36), ForeignKey("unidades.id"), nullable=True)
    perfil_id = Column(String(36), ForeignKey("perfis.id"), nullable=False)
    concedido_por = Column(String(36), ForeignKey("usuarios.id"))
    concedido_em = Column(DateTime, default=datetime.utcnow)

    usuario = relationship("Usuario", back_populates="vinculos", foreign_keys=[usuario_id])
    unidade = relationship("Unidade", back_populates="vinculos")
    perfil = relationship("Perfil", back_populates="vinculos")
