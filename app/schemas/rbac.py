from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UsuarioCreate(BaseModel):
    nome_completo: str
    email: EmailStr
    senha: str
    perfil_id: str
    perfil_ids: list[str] = []
    unidade_ids: list[str] = []


class UsuarioUpdate(BaseModel):
    nome_completo: str | None = None
    email: EmailStr | None = None
    senha: str | None = None
    status: str | None = None
    perfil_id: str | None = None
    perfil_ids: list[str] | None = None
    unidade_ids: list[str] | None = None


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    id_usuario: str
    login: str
    email: str
    nome_completo: str
    status: str
    criado_em: datetime | None


class PerfilCreate(BaseModel):
    nome: str
    descricao: str | None = None
    requer_setor: bool = True


class PerfilOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    nome: str
    descricao: str | None
    tipo: str
    requer_setor: bool
    ativo: bool


class EnteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    nome_ente: str
    cnpj_ente: str
    uf: str
    tipo_ente: str
    representante_legal: str | None = None
    cpf_representante: str | None = None
    data_inicio_processo: date | None = None
    data_fim_processo: date | None = None
    codigo_siafi: str | None = None
    email_contato: str | None = None
    telefone_contato: str | None = None
    cep: str | None = None
    cidade: str | None = None
    tipo_logradouro: str | None = None
    logradouro: str | None = None
    numero: str | None = None
    bairro: str | None = None
    complemento: str | None = None
    nome_ug: str | None = None
    cnpj_ug: str | None = None
    nivel_atual: str | None = None
    nivel_pretendido: str | None = None
    entidade_certificadora: str | None = None
    num_segurados: int | None = None
    observacoes: str | None = None
    ativo: bool = True


class EnteUpdate(BaseModel):
    nome_ente: str | None = None
    cnpj_ente: str | None = None
    uf: str | None = None
    tipo_ente: str | None = None
    representante_legal: str | None = None
    cpf_representante: str | None = None
    data_inicio_processo: date | None = None
    data_fim_processo: date | None = None
    codigo_siafi: str | None = None
    email_contato: str | None = None
    telefone_contato: str | None = None
    cep: str | None = None
    cidade: str | None = None
    tipo_logradouro: str | None = None
    logradouro: str | None = None
    numero: str | None = None
    bairro: str | None = None
    complemento: str | None = None
    nome_ug: str | None = None
    cnpj_ug: str | None = None
    nivel_atual: str | None = None
    nivel_pretendido: str | None = None
    entidade_certificadora: str | None = None
    num_segurados: int | None = None
    observacoes: str | None = None


class UnidadeCreate(BaseModel):
    sigla: str
    nome: str
    descricao: str | None = None


class UnidadeUpdate(BaseModel):
    sigla: str | None = None
    nome: str | None = None
    descricao: str | None = None
    ativo: bool | None = None


class UnidadeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    sigla: str
    nome: str
    descricao: str | None
    ativo: bool
