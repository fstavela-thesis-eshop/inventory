from uuid import UUID

from pydantic import BaseModel
from pydantic import ConfigDict


class ProductBase(BaseModel):
    name: str
    description: str
    category_id: UUID
    price: float

    model_config = ConfigDict(extra="forbid")


class ProductCreate(ProductBase):
    stock_quantity: int | None = None


class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    category_id: UUID | None = None
    stock_quantity: int | None = None
    price: float | None = None

    model_config = ConfigDict(extra="forbid")


class ProductQuantityUpdate(BaseModel):
    id: UUID
    stock_quantity_dif: int

    model_config = ConfigDict(extra="forbid")


class ProductResponse(ProductBase):
    id: UUID
    stock_quantity: int
