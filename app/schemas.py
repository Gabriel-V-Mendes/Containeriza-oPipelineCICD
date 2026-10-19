"""Schemas Pydantic: validam a entrada e definem o formato da saída da API."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ItemCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100, examples=["Docker"])
    description: str | None = Field(default=None, max_length=500)


class ItemUpdate(BaseModel):
    """Atualização parcial (PATCH): só os campos enviados são alterados."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)

    @field_validator("name")
    @classmethod
    def name_not_null(cls, value: str | None) -> str | None:
        # Só roda quando "name" é ENVIADO (defaults não são validados): omitir o
        # campo é permitido, mas mandar "name": null não, pois a coluna é NOT NULL.
        if value is None:
            raise ValueError("name não pode ser nulo")
        return value


class ItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime
