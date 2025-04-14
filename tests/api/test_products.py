import logging
from typing import Any
from unittest.mock import MagicMock
from uuid import UUID
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pytest_mock.plugin import MockerFixture
from sqlalchemy import Select
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.db.models import Category
from src.db.models import Product
from tests.helpers import gen_headers
from tests.helpers import generate_change_stock_quantity_data
from tests.helpers import generate_create_product_data
from tests.helpers import generate_random_db_category
from tests.helpers import generate_random_db_product
from tests.helpers import validate_db_product
from tests.helpers import validate_product_response

logger = logging.getLogger(__name__)


@pytest.mark.parametrize("is_admin", (True, False))
def test_get_products_all(
    api_client: TestClient, mock_db: MagicMock, mocker: MockerFixture, is_admin: bool
) -> None:
    mock_product1 = generate_random_db_product(in_stock=True)
    mock_product2 = generate_random_db_product(in_stock=False)

    mock_return = mocker.Mock()

    def _scalars(query: Select[Product]) -> mocker.Mock:
        assert str(query.compile()) == str(select(Product).compile())
        return mock_return

    mock_db.scalars = _scalars
    mock_return.all.return_value = [mock_product1, mock_product2]

    response = api_client.get(
        "/products",
        headers=gen_headers(is_admin),
    )

    assert response.status_code == 200
    response_json = response.json()
    assert isinstance(response_json, list)

    assert len(response_json) == 2
    validate_product_response(response_json[0], mock_product1)
    validate_product_response(response_json[1], mock_product2)


@pytest.mark.parametrize("is_admin", (True, False))
def test_get_products_empty(
    api_client: TestClient, mock_db: MagicMock, mocker: MockerFixture, is_admin: bool
) -> None:
    mock_return = mocker.Mock()

    def _scalars(query: Select[Product]) -> mocker.Mock:
        assert str(query.compile()) == str(select(Product).compile())
        return mock_return

    mock_db.scalars = _scalars
    mock_return.all.return_value = []

    response = api_client.get(
        "/products",
        headers=gen_headers(is_admin),
    )

    assert response.status_code == 200
    response_json = response.json()
    assert isinstance(response_json, list)
    assert len(response_json) == 0


@pytest.mark.parametrize("is_admin", (True, False))
def test_get_products_by_product_name(
    api_client: TestClient, mock_db: MagicMock, mocker: MockerFixture, is_admin: bool
) -> None:
    mock_product = generate_random_db_product()

    mock_return = mocker.Mock()

    def _scalars(query: Select[Product]) -> mocker.Mock:
        assert str(query.compile()) == str(
            select(Product)
            .where(Product.name.ilike(f"%{mock_product.name}%"))
            .compile()
        )
        return mock_return

    mock_db.scalars = _scalars
    mock_return.all.return_value = [mock_product]

    response = api_client.get(
        f"/products?product_name={mock_product.name}",
        headers=gen_headers(is_admin),
    )

    assert response.status_code == 200
    response_json = response.json()
    assert isinstance(response_json, list)

    assert len(response_json) == 1
    validate_product_response(response_json[0], mock_product)


@pytest.mark.parametrize("is_admin", (True, False))
def test_get_products_by_category_name(
    api_client: TestClient, mock_db: MagicMock, mocker: MockerFixture, is_admin: bool
) -> None:
    mock_category = generate_random_db_category()
    mock_product = generate_random_db_product(category_id=mock_category.id)  # type: ignore[arg-type]

    mock_return = mocker.Mock()

    def _scalar(query: Select[Category]) -> UUID:
        assert str(query.compile()) == str(
            select(Category.id).where(Category.name == mock_category.name).compile()
        )
        return mock_category.id  # type: ignore[return-value]

    def _scalars(query: Select[Product]) -> mocker.Mock:
        assert str(query.compile()) == str(
            select(Product).where(Product.category_id == mock_category.id).compile()
        )
        return mock_return

    mock_db.scalar = _scalar
    mock_db.scalars = _scalars
    mock_return.all.return_value = [mock_product]

    response = api_client.get(
        f"/products?category_name={mock_category.name}",
        headers=gen_headers(is_admin),
    )

    assert response.status_code == 200
    response_json = response.json()
    assert isinstance(response_json, list)

    assert len(response_json) == 1
    validate_product_response(response_json[0], mock_product)


@pytest.mark.parametrize("is_admin", (True, False))
def test_get_products_by_category_name_category_not_found(
    api_client: TestClient, mock_db: MagicMock, is_admin: bool
) -> None:
    mock_category = generate_random_db_category()

    def _scalar(query: Select[Category]) -> None:
        assert str(query.compile()) == str(
            select(Category.id).where(Category.name == mock_category.name).compile()
        )
        return None

    mock_db.scalar = _scalar

    response = api_client.get(
        f"/products?category_name={mock_category.name}",
        headers=gen_headers(is_admin),
    )

    assert response.status_code == 200
    response_json = response.json()
    assert isinstance(response_json, list)

    assert len(response_json) == 0


@pytest.mark.parametrize("is_admin", (True, False))
def test_get_products_is_in_stock(
    api_client: TestClient, mock_db: MagicMock, mocker: MockerFixture, is_admin: bool
) -> None:
    mock_product = generate_random_db_product(in_stock=True)

    mock_return = mocker.Mock()

    def _scalars(query: Select[Product]) -> mocker.Mock:
        assert str(query.compile()) == str(
            select(Product).where(Product.stock_quantity > 0).compile()
        )
        return mock_return

    mock_db.scalars = _scalars
    mock_return.all.return_value = [mock_product]

    response = api_client.get(
        "/products?is_in_stock=true",
        headers=gen_headers(is_admin),
    )

    assert response.status_code == 200
    response_json = response.json()
    assert isinstance(response_json, list)

    assert len(response_json) == 1
    validate_product_response(response_json[0], mock_product)


@pytest.mark.parametrize("is_admin", (True, False))
def test_get_products_is_not_in_stock(
    api_client: TestClient, mock_db: MagicMock, mocker: MockerFixture, is_admin: bool
) -> None:
    mock_product = generate_random_db_product(in_stock=False)

    mock_return = mocker.Mock()

    def _scalars(query: Select[Product]) -> mocker.Mock:
        assert str(query.compile()) == str(
            select(Product).where(Product.stock_quantity == 0).compile()
        )
        return mock_return

    mock_db.scalars = _scalars
    mock_return.all.return_value = [mock_product]

    response = api_client.get(
        "/products?is_in_stock=false",
        headers=gen_headers(is_admin),
    )

    assert response.status_code == 200
    response_json = response.json()
    assert isinstance(response_json, list)

    assert len(response_json) == 1
    validate_product_response(response_json[0], mock_product)


@pytest.mark.parametrize("product_id", ("str", "123", str(uuid4()) + "a"))
@pytest.mark.parametrize("is_admin", (True, False))
def test_get_product_wrong_id(
    api_client: TestClient, product_id: str, is_admin: bool
) -> None:
    response = api_client.get(
        f"/products/{product_id}",
        headers=gen_headers(is_admin),
    )
    assert response.status_code == 422


@pytest.mark.parametrize("is_admin", (True, False))
def test_get_product_not_found(
    api_client: TestClient, mock_db: MagicMock, is_admin: bool
) -> None:
    product_id = str(uuid4())

    def _get_product(_: Any, input_product_id: UUID) -> None:
        assert str(input_product_id) == product_id
        return None

    mock_db.get = _get_product

    response = api_client.get(
        f"/products/{product_id}",
        headers=gen_headers(is_admin),
    )
    assert response.status_code == 404


@pytest.mark.parametrize("is_admin", (True, False))
def test_get_product_correct(
    api_client: TestClient, mock_db: MagicMock, is_admin: bool
) -> None:
    mock_product = generate_random_db_product()

    def _get_product(_: Any, input_product_id: UUID) -> Product:
        assert input_product_id == mock_product.id
        return mock_product

    mock_db.get = _get_product

    response = api_client.get(
        f"/products/{str(mock_product.id)}",
        headers=gen_headers(is_admin),
    )

    assert response.status_code == 200
    response_json = response.json()
    assert isinstance(response_json, dict)

    validate_product_response(response_json, mock_product)


def test_create_product_correct(api_client: TestClient, mock_db: MagicMock) -> None:
    product_data = generate_create_product_data()
    expected_products = []

    def _add_product(product: Product) -> None:
        validate_db_product(product, product_data)
        expected_products.append(product)

    mock_db.add = _add_product

    response = api_client.post(
        "/products/create", json=product_data, headers=gen_headers(True)
    )

    mock_db.commit.assert_called_once()

    assert response.status_code == 201
    response_json = response.json()
    assert isinstance(response_json, dict)

    validate_product_response(response_json, expected_products[0])


def test_create_product_forbidden(api_client: TestClient) -> None:
    product_data = generate_create_product_data()

    response = api_client.post(
        "/products/create", json=product_data, headers=gen_headers(False)
    )
    assert response.status_code == 403


@pytest.mark.parametrize(
    "field",
    ("category_id", "name", "description", "price"),
)
def test_create_product_missing_field(api_client: TestClient, field: str) -> None:
    product_data = generate_create_product_data()
    product_data.pop(field)

    response = api_client.post(
        "/products/create", json=product_data, headers=gen_headers(True)
    )
    assert response.status_code == 422


def test_create_product_additional_field(api_client: TestClient) -> None:
    product_data = generate_create_product_data()
    product_data["additional"] = "abcd"

    response = api_client.post(
        "/products/create", json=product_data, headers=gen_headers(True)
    )
    assert response.status_code == 422


def test_create_product_db_error(api_client: TestClient, mock_db: MagicMock) -> None:
    product_data = generate_create_product_data()

    mock_db.add.side_effect = IntegrityError(
        statement="DB error", params=None, orig=BaseException("DB error\nVery serious")
    )

    response = api_client.post(
        "/products/create", json=product_data, headers=gen_headers(True)
    )
    assert response.status_code == 400
    mock_db.rollback.assert_called_once()


def test_update_product_forbidden(api_client: TestClient) -> None:
    product_data = generate_create_product_data()

    response = api_client.patch(
        f"/products/update/{str(uuid4())}",
        json=product_data,
        headers=gen_headers(False),
    )
    assert response.status_code == 403


@pytest.mark.parametrize("product_id", ("str", "123", str(uuid4()) + "a"))
def test_update_product_wrong_id(api_client: TestClient, product_id: str) -> None:
    update_data = generate_create_product_data()

    response = api_client.patch(
        f"/products/update/{product_id}",
        json=update_data,
        headers=gen_headers(True),
    )
    assert response.status_code == 422


def test_update_product_not_found(api_client: TestClient, mock_db: MagicMock) -> None:
    product_id = str(uuid4())

    def _get_product(_: Any, input_product_id: UUID) -> None:
        assert str(input_product_id) == product_id
        return None

    mock_db.get = _get_product

    update_data = generate_create_product_data()

    response = api_client.patch(
        f"/products/update/{product_id}",
        json=update_data,
        headers=gen_headers(True),
    )
    assert response.status_code == 404


def test_update_product_db_error(api_client: TestClient, mock_db: MagicMock) -> None:
    mock_product = generate_random_db_product()

    def _get_product(_: Any, product_id: str) -> Product:
        assert product_id == mock_product.id
        return mock_product

    mock_db.get = _get_product

    update_data = generate_create_product_data()

    mock_db.commit.side_effect = IntegrityError(
        statement="DB error", params=None, orig=BaseException("DB error\nVery serious")
    )

    response = api_client.patch(
        f"/products/update/{str(mock_product.id)}",
        json=update_data,
        headers=gen_headers(True),
    )
    assert response.status_code == 400
    mock_db.rollback.assert_called_once()


def test_update_product_correct(api_client: TestClient, mock_db: MagicMock) -> None:
    mock_product = generate_random_db_product()
    orig_id = mock_product.id

    def _get_product(_: Any, input_product_id: str) -> Product:
        assert input_product_id == mock_product.id
        return mock_product

    mock_db.get = _get_product

    update_data = generate_create_product_data()

    response = api_client.patch(
        f"/products/update/{str(mock_product.id)}",
        json=update_data,
        headers=gen_headers(True),
    )

    mock_db.commit.assert_called_once()
    assert mock_product.id == orig_id
    validate_db_product(mock_product, update_data)

    assert response.status_code == 200
    response_json = response.json()
    assert isinstance(response_json, dict)

    validate_product_response(response_json, mock_product)


def test_delete_product_forbidden(api_client: TestClient) -> None:
    response = api_client.delete(
        f"/products/{str(uuid4())}", headers=gen_headers(False)
    )
    assert response.status_code == 403


@pytest.mark.parametrize("product_id", ("str", "123", str(uuid4()) + "a"))
def test_delete_product_wrong_id(api_client: TestClient, product_id: str) -> None:
    response = api_client.delete(
        f"/products/{product_id}",
        headers=gen_headers(True),
    )
    assert response.status_code == 422


def test_delete_product_not_found(api_client: TestClient, mock_db: MagicMock) -> None:
    product_id = str(uuid4())

    def _get_product(_: Any, input_product_id: UUID) -> None:
        assert str(input_product_id) == product_id
        return None

    mock_db.get = _get_product

    response = api_client.delete(
        f"/products/{product_id}",
        headers=gen_headers(True),
    )
    assert response.status_code == 404


def test_delete_product_correct(api_client: TestClient, mock_db: MagicMock) -> None:
    mock_product = generate_random_db_product()

    def _get_product(_: Any, input_product_id: str) -> Product:
        assert input_product_id == mock_product.id
        return mock_product

    def _delete_product(product: Product) -> None:
        assert product == mock_product

    mock_db.get = _get_product
    mock_db.delete = _delete_product

    response = api_client.delete(
        f"/products/{str(mock_product.id)}",
        headers=gen_headers(True),
    )

    mock_db.commit.assert_called_once()
    assert response.status_code == 204


def test_change_stock_quantity_forbidden(api_client: TestClient) -> None:
    quantity_data = [generate_change_stock_quantity_data()]

    response = api_client.patch(
        "/products/stock", json=quantity_data, headers=gen_headers(False)
    )
    assert response.status_code == 403


def test_change_stock_quantity_not_found(
    api_client: TestClient, mock_db: MagicMock
) -> None:
    product = generate_random_db_product()

    def _get_product(_: Any, input_product_id: UUID) -> None:
        assert input_product_id == product.id
        return None

    mock_db.get = _get_product

    quantity_data = [generate_change_stock_quantity_data(product_id=str(product.id))]

    response = api_client.patch(
        "/products/stock",
        json=quantity_data,
        headers=gen_headers(True),
    )
    assert response.status_code == 404
    mock_db.rollback.assert_called_once()
    mock_db.commit.assert_not_called()


def test_change_stock_quantity_lower_than_zero(
    api_client: TestClient, mock_db: MagicMock
) -> None:
    product = generate_random_db_product(in_stock=False)

    def _get_product(_: Any, input_product_id: UUID) -> Product:
        assert input_product_id == product.id
        return product

    mock_db.get = _get_product

    quantity_data = [
        generate_change_stock_quantity_data(
            product_id=str(product.id), stock_quantity_dif=-5
        )
    ]

    response = api_client.patch(
        "/products/stock",
        json=quantity_data,
        headers=gen_headers(True),
    )
    assert response.status_code == 400
    mock_db.rollback.assert_called_once()
    mock_db.commit.assert_not_called()


def test_change_stock_quantity_correct(
    api_client: TestClient, mock_db: MagicMock
) -> None:
    product = generate_random_db_product()
    orig_stock_quantity = product.stock_quantity

    def _get_product(_: Any, input_product_id: UUID) -> Product:
        assert input_product_id == product.id
        return product

    mock_db.get = _get_product

    quantity_data = [
        generate_change_stock_quantity_data(
            product_id=str(product.id), stock_quantity_dif=10
        )
    ]

    response = api_client.patch(
        "/products/stock",
        json=quantity_data,
        headers=gen_headers(True),
    )

    mock_db.commit.assert_called_once()
    assert product.stock_quantity == orig_stock_quantity + 10

    assert response.status_code == 200
    response_json = response.json()
    assert isinstance(response_json, list)
    assert len(response_json) == 1

    validate_product_response(response_json[0], product)
