from uuid import uuid4

from sqlalchemy import UUID
from sqlalchemy import Column
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Product(Base):  # type: ignore[valid-type, misc]
    __tablename__ = "products"

    id = Column(
        UUID(as_uuid=True), nullable=False, unique=True, primary_key=True, default=uuid4
    )
    category_id: Column[UUID[str]] = Column(
        ForeignKey("categories.id"), nullable=False, index=True
    )
    name = Column(String(64), nullable=False, unique=True, index=True)
    description = Column(String(1024))
    stock_quantity = Column(Integer, nullable=False, default=0)


class Category(Base):  # type: ignore[valid-type, misc]
    __tablename__ = "categories"

    id = Column(
        UUID(as_uuid=True), nullable=False, unique=True, primary_key=True, default=uuid4
    )
    name = Column(String(32), nullable=False, unique=True, index=True)
    description = Column(String(1024))
