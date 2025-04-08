from random import choices
from random import randint
from random import uniform
from string import ascii_letters
from string import digits
from string import punctuation
from typing import Any
from uuid import UUID
from uuid import uuid4

from src.db.models import Category
from src.db.models import Product

EXPECTED_PRODUCT_RESPONSE_FIELDS = {
    "id",
    "name",
    "description",
    "category_id",
    "price",
    "stock_quantity",
}


EXPECTED_CATEGORY_RESPONSE_FIELDS = {
    "id",
    "name",
    "description",
}


def gen_str(
    length: int = 10,
    *,
    use_letters: bool = True,
    use_digits: bool = True,
    use_punctuation: bool = True,
) -> str:
    symbols = ""
    if use_letters:
        symbols += ascii_letters
    if use_digits:
        symbols += digits
    if use_punctuation:
        symbols += punctuation
    return "".join(choices(symbols, k=length))


def gen_headers(is_admin: bool = False) -> dict[str, str]:
    return {"x-customer-id": str(uuid4()), "x-is-admin": str(is_admin).lower()}


def generate_random_db_category() -> Category:
    return Category(id=uuid4(), name=gen_str(10), description=gen_str(50))


def generate_random_db_product(
    *, category_id: UUID | None = None, in_stock: bool = True
) -> Product:
    return Product(
        id=uuid4(),
        category_id=category_id or generate_random_db_category().id,
        name=gen_str(),
        description=gen_str(50),
        price=round(uniform(10, 1000), 2),
        stock_quantity=randint(1, 500) if in_stock else 0,
    )


def generate_create_product_data(
    *, category_id: str | None = None, in_stock: bool = True
) -> dict[str, str | float | int]:
    return {
        "category_id": category_id or str(generate_random_db_category().id),
        "name": gen_str(),
        "description": gen_str(50),
        "price": round(uniform(10, 1000), 2),
        "stock_quantity": randint(1, 500) if in_stock else 0,
    }


def generate_create_category_data() -> dict[str, str]:
    return {
        "name": gen_str(),
        "description": gen_str(50),
    }


def generate_change_stock_quantity_data(
    *, product_id: str | None = None, stock_quantity_dif: int | None = None
) -> dict[str, str | int]:
    return {
        "id": product_id or str(generate_random_db_product().id),
        "stock_quantity_dif": stock_quantity_dif or randint(1, 500),
    }


def validate_product_response(
    response_product: dict[str, Any], expected_product: Product
) -> None:
    assert len(response_product.keys()) == len(EXPECTED_PRODUCT_RESPONSE_FIELDS)
    assert set(response_product.keys()) == EXPECTED_PRODUCT_RESPONSE_FIELDS
    for field in EXPECTED_PRODUCT_RESPONSE_FIELDS:
        expected_value = getattr(expected_product, field)
        if isinstance(expected_value, UUID):
            expected_value = str(expected_value)
        assert response_product[field] == expected_value, (
            f"{response_product[field]} != {expected_value}"
        )


def validate_category_response(
    response_category: dict[str, Any], expected_category: Category
) -> None:
    assert len(response_category.keys()) == len(EXPECTED_CATEGORY_RESPONSE_FIELDS)
    assert set(response_category.keys()) == EXPECTED_CATEGORY_RESPONSE_FIELDS
    for field in EXPECTED_CATEGORY_RESPONSE_FIELDS:
        expected_value = getattr(expected_category, field)
        if isinstance(expected_value, UUID):
            expected_value = str(expected_value)
        assert response_category[field] == expected_value, (
            f"{response_category[field]} != {expected_value}"
        )


def validate_db_product(db_product: Product, expected_data: dict[str, Any]) -> None:
    assert str(db_product.category_id) == expected_data["category_id"]
    assert db_product.name == expected_data["name"]
    assert db_product.description == expected_data["description"]
    assert db_product.price == expected_data["price"]
    assert db_product.stock_quantity == expected_data["stock_quantity"]


def validate_db_category(db_category: Category, expected_data: dict[str, Any]) -> None:
    assert db_category.name == expected_data["name"]
    assert db_category.description == expected_data["description"]
