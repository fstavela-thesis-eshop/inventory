import logging
from typing import Annotated
from typing import cast
from uuid import UUID

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Header
from fastapi import HTTPException
from fastapi import status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db.models import Category
from db.session import get_db
from schemas.category_schemas import CategoryBase
from schemas.category_schemas import CategoryResponse
from schemas.category_schemas import CategoryUpdate

logger = logging.getLogger(__name__)


categories_router = APIRouter()


@categories_router.get("", response_model=list[CategoryResponse])
def get_categories(
    db: Annotated[Session, Depends(get_db)],
    name: str | None = None,
) -> list[Category]:
    filters = []

    if name:
        filters.append(Category.name.ilike(f"%{name}%"))

    query = select(Category).where(*filters)
    return cast(list[Category], db.scalars(query).all())


@categories_router.get(
    "/{category_id}",
    response_model=CategoryResponse,
    responses={status.HTTP_404_NOT_FOUND: {}},
)
def get_category(
    category_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> Category:
    db_category = db.get(Category, category_id)
    if not db_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )

    return db_category


@categories_router.post(
    "/create",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    responses={status.HTTP_400_BAD_REQUEST: {}, status.HTTP_403_FORBIDDEN: {}},
)
def create_category(
    input_category: CategoryBase,
    x_is_admin: Annotated[bool, Header()],
    db: Annotated[Session, Depends(get_db)],
) -> Category:
    if not x_is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You don't have admin rights"
        )

    db_category = Category(
        name=input_category.name,
        description=input_category.description,
    )

    try:
        db.add(db_category)
        db.commit()
    except IntegrityError as err:
        logger.error(f"Error while creating a new category: {err.args}")
        err_message = err.args[0].split("\n")[-2]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=err_message
        ) from err

    db.refresh(db_category)
    return db_category


@categories_router.patch(
    "/{category_id}",
    response_model=CategoryResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {},
        status.HTTP_403_FORBIDDEN: {},
        status.HTTP_404_NOT_FOUND: {},
    },
)
def update_category(
    category_id: UUID,
    input_category: CategoryUpdate,
    x_is_admin: Annotated[bool, Header()],
    db: Annotated[Session, Depends(get_db)],
) -> Category:
    if not x_is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You don't have admin rights"
        )

    db_category = db.get(Category, category_id)
    if not db_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )

    update_data = input_category.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(db_category, k, v)

    try:
        db.commit()
    except IntegrityError as err:
        logger.error(f"Error while updating a category: {err.args}")
        err_message = err.args[0].split("\n")[-2]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=err_message
        ) from err

    db.refresh(db_category)
    return db_category


@categories_router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_403_FORBIDDEN: {},
        status.HTTP_404_NOT_FOUND: {},
    },
)
def delete_category(
    category_id: UUID,
    x_is_admin: Annotated[bool, Header()],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    if not x_is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You don't have admin rights"
        )

    db_category = db.get(Category, category_id)
    if not db_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )

    db.delete(db_category)
    db.commit()
