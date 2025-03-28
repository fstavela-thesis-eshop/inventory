from uuid import UUID

from pydantic import BaseModel


class ProductBase(BaseModel):
    name: str
    description: str
    category_id: UUID

    class Config:
        extra = "forbid"


class ProductCreate(ProductBase):
    stock_quantity: int | None = None


class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    category_id: UUID | None = None
    stock_quantity: int | None = None

    class Config:
        extra = "forbid"


class ProductResponse(ProductBase):
    id: UUID
    stock_quantity: int
