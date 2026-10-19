from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UsuarioCreate(BaseModel):
    nome_completo: str
    email: EmailStr
    senha: str
    perfil_id: str
    unidade_ids: list[str] = []


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


class UnidadeCreate(BaseModel):
    sigla: str
    nome: str
    descricao: str | None = None


class UnidadeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    sigla: str
    nome: str
    descricao: str | None
    ativo: bool
