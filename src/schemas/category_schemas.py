from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict


class CategoryBase(BaseModel):
    name: str
    description: str

    model_config = ConfigDict(extra="forbid")


class CategoryUpdate(BaseModel):
    name: str | None = None
    description: str | None = None

    model_config = ConfigDict(extra="forbid")


class CategoryResponse(CategoryBase):
    id: UUID
