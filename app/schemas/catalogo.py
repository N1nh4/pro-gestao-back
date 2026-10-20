"""Schemas do catálogo do manual: manual, dimensão, requisito e item."""

from pydantic import BaseModel, ConfigDict, Field


class ManualCreate(BaseModel):
    nome_manual: str = Field(min_length=1, max_length=200)
    versao_manual: str = Field(min_length=1, max_length=20)


class ManualUpdate(BaseModel):
    nome_manual: str | None = Field(default=None, min_length=1, max_length=200)
    versao_manual: str | None = Field(default=None, min_length=1, max_length=20)


class ManualOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_manual: int
    nome_manual: str
    versao_manual: str


class DimensaoCreate(BaseModel):
    nome_dimensao: str = Field(min_length=1, max_length=150)


class DimensaoUpdate(BaseModel):
    nome_dimensao: str | None = Field(default=None, min_length=1, max_length=150)


class DimensaoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_dimensao: int
    nome_dimensao: str


class RequisitoCreate(BaseModel):
    id_manual: int
    id_dimensao: int
    cod_requisito: str = Field(min_length=1, max_length=10)
    nome_requisito: str = Field(min_length=1, max_length=200)


class RequisitoUpdate(BaseModel):
    id_manual: int | None = None
    id_dimensao: int | None = None
    cod_requisito: str | None = Field(default=None, min_length=1, max_length=10)
    nome_requisito: str | None = Field(default=None, min_length=1, max_length=200)


class RequisitoCatalogoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_requisito: int
    id_manual: int
    id_dimensao: int
    cod_requisito: str
    nome_requisito: str
    nome_dimensao: str = ""
    total_itens: int = 0


class ItemCreate(BaseModel):
    id_requisito: int
    nome_item: str = Field(min_length=1, max_length=300)
    nivel: str  # I | II | III | IV
    descricao: str | None = None


class ItemUpdate(BaseModel):
    id_requisito: int | None = None
    nome_item: str | None = Field(default=None, min_length=1, max_length=300)
    nivel: str | None = None
    descricao: str | None = None


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_item: int
    id_requisito: int
    nome_item: str
    nivel: str
    descricao: str | None
