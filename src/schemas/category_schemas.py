from uuid import UUID

from pydantic import BaseModel


class CategoryBase(BaseModel):
    name: str
    description: str

    class Config:
        extra = "forbid"


class CategoryUpdate(BaseModel):
    name: str | None = None
    description: str | None = None

    class Config:
        extra = "forbid"


class CategoryResponse(CategoryBase):
    id: UUID
