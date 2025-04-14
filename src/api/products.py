import logging
from typing import Annotated
from typing import cast
from uuid import UUID
from uuid import uuid4

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.helpers import HeaderNoSchema
from db.models import Category
from db.models import Product
from db.session import get_db
from schemas.product_schemas import ProductCreate
from schemas.product_schemas import ProductQuantityUpdate
from schemas.product_schemas import ProductResponse
from schemas.product_schemas import ProductUpdate

logger = logging.getLogger(__name__)


products_router = APIRouter()


@products_router.get("", response_model=list[ProductResponse])
def get_products(
    db: Annotated[Session, Depends(get_db)],
    product_name: str | None = None,
    category_name: str | None = None,
    is_in_stock: bool | None = None,
) -> list[Product]:
    filters = []

    if product_name:
        filters.append(Product.name.ilike(f"%{product_name}%"))

    if category_name:
        db_category_id = db.scalar(
            select(Category.id).where(Category.name == category_name)
        )
        if not db_category_id:
            return []
        filters.append(Product.category_id == db_category_id)

    if is_in_stock:
        filters.append(Product.stock_quantity > 0)
    elif is_in_stock is False:
        filters.append(Product.stock_quantity == 0)

    query = select(Product).where(*filters)
    return cast(list[Product], db.scalars(query).all())


@products_router.get(
    "/{product_id}",
    response_model=ProductResponse,
    responses={status.HTTP_404_NOT_FOUND: {}},
)
def get_product(
    product_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> Product:
    db_product = db.get(Product, product_id)
    if not db_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    return db_product


@products_router.post(
    "/create",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    responses={status.HTTP_400_BAD_REQUEST: {}, status.HTTP_403_FORBIDDEN: {}},
)
def create_product(
    input_product: ProductCreate,
    x_is_admin: Annotated[bool, HeaderNoSchema()],
    db: Annotated[Session, Depends(get_db)],
) -> Product:
    if not x_is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You don't have admin rights"
        )

    db_product = Product(
        id=uuid4(),
        name=input_product.name,
        description=input_product.description,
        category_id=input_product.category_id,
        stock_quantity=input_product.stock_quantity or 0,
        price=input_product.price,
    )

    try:
        db.add(db_product)
    except IntegrityError as err:
        logger.error(f"Error while creating a new product: {err.args}")
        db.rollback()
        err_message = err.args[0].split("\n")[-2]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=err_message
        ) from err

    return db_product


@products_router.patch(
    "/update/{product_id}",
    response_model=ProductResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {},
        status.HTTP_403_FORBIDDEN: {},
        status.HTTP_404_NOT_FOUND: {},
    },
)
def update_product(
    product_id: UUID,
    input_product: ProductUpdate,
    x_is_admin: Annotated[bool, HeaderNoSchema()],
    db: Annotated[Session, Depends(get_db)],
) -> Product:
    if not x_is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You don't have admin rights"
        )

    db_product = db.get(Product, product_id)
    if not db_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    update_data = input_product.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(db_product, k, v)

    try:
        db.commit()
    except IntegrityError as err:
        logger.error(f"Error while updating a product: {err.args}")
        db.rollback()
        err_message = err.args[0].split("\n")[-2]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=err_message
        ) from err

    db.refresh(db_product)
    return db_product


@products_router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_403_FORBIDDEN: {},
        status.HTTP_404_NOT_FOUND: {},
    },
)
def delete_product(
    product_id: UUID,
    x_is_admin: Annotated[bool, HeaderNoSchema()],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    if not x_is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You don't have admin rights"
        )

    db_product = db.get(Product, product_id)
    if not db_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    db.delete(db_product)
    db.commit()


@products_router.patch(
    "/stock",
    response_model=list[ProductResponse],
    responses={
        status.HTTP_400_BAD_REQUEST: {},
        status.HTTP_403_FORBIDDEN: {},
        status.HTTP_404_NOT_FOUND: {},
    },
)
def change_stock_quantity(
    input_products: list[ProductQuantityUpdate],
    x_is_admin: Annotated[bool, HeaderNoSchema()],
    db: Annotated[Session, Depends(get_db)],
) -> list[Product]:
    if not x_is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You don't have admin rights"
        )

    db_products = []
    for input_product in input_products:
        db_product = db.get(Product, input_product.id)
        if not db_product:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product not found: {input_product.id}",
            )

        if db_product.stock_quantity + input_product.stock_quantity_dif < 0:
            db.rollback()
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail=f"Not enough product in stock: {input_product.id}",
            )

        db_product.stock_quantity += input_product.stock_quantity_dif
        db_products.append(db_product)

    db.commit()
    return db_products
