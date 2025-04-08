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
from tests.helpers import gen_headers
from tests.helpers import generate_create_category_data
from tests.helpers import generate_random_db_category
from tests.helpers import validate_category_response
from tests.helpers import validate_db_category

logger = logging.getLogger(__name__)


@pytest.mark.parametrize("is_admin", (True, False))
def test_get_categories_all(
    api_client: TestClient, mock_db: MagicMock, mocker: MockerFixture, is_admin: bool
) -> None:
    mock_category1 = generate_random_db_category()
    mock_category2 = generate_random_db_category()

    mock_return = mocker.Mock()

    def _scalars(query: Select[Category]) -> mocker.Mock:
        assert str(query.compile()) == str(select(Category).compile())
        return mock_return

    mock_db.scalars = _scalars
    mock_return.all.return_value = [mock_category1, mock_category2]

    response = api_client.get(
        "/categories",
        headers=gen_headers(is_admin),
    )

    assert response.status_code == 200
    response_json = response.json()
    assert isinstance(response_json, list)

    assert len(response_json) == 2
    validate_category_response(response_json[0], mock_category1)
    validate_category_response(response_json[1], mock_category2)


@pytest.mark.parametrize("is_admin", (True, False))
def test_get_categories_empty(
    api_client: TestClient, mock_db: MagicMock, mocker: MockerFixture, is_admin: bool
) -> None:
    mock_return = mocker.Mock()

    def _scalars(query: Select[Category]) -> mocker.Mock:
        assert str(query.compile()) == str(select(Category).compile())
        return mock_return

    mock_db.scalars = _scalars
    mock_return.all.return_value = []

    response = api_client.get(
        "/categories",
        headers=gen_headers(is_admin),
    )

    assert response.status_code == 200
    response_json = response.json()
    assert isinstance(response_json, list)
    assert len(response_json) == 0


@pytest.mark.parametrize("is_admin", (True, False))
def test_get_categories_by_name(
    api_client: TestClient, mock_db: MagicMock, mocker: MockerFixture, is_admin: bool
) -> None:
    mock_category = generate_random_db_category()

    mock_return = mocker.Mock()

    def _scalars(query: Select[Category]) -> mocker.Mock:
        assert str(query.compile()) == str(
            select(Category)
            .where(Category.name.ilike(f"%{mock_category.name}%"))
            .compile()
        )
        return mock_return

    mock_db.scalars = _scalars
    mock_return.all.return_value = [mock_category]

    response = api_client.get(
        f"/categories?name={mock_category.name}",
        headers=gen_headers(is_admin),
    )

    assert response.status_code == 200
    response_json = response.json()
    assert isinstance(response_json, list)

    assert len(response_json) == 1
    validate_category_response(response_json[0], mock_category)


@pytest.mark.parametrize("category_id", ("str", "123", str(uuid4()) + "a"))
@pytest.mark.parametrize("is_admin", (True, False))
def test_get_category_wrong_id(
    api_client: TestClient, category_id: str, is_admin: bool
) -> None:
    response = api_client.get(
        f"/categories/{category_id}",
        headers=gen_headers(is_admin),
    )
    assert response.status_code == 422


@pytest.mark.parametrize("is_admin", (True, False))
def test_get_category_not_found(
    api_client: TestClient, mock_db: MagicMock, is_admin: bool
) -> None:
    category_id = str(uuid4())

    def _get_category(_: Any, input_product_id: UUID) -> None:
        assert str(input_product_id) == category_id
        return None

    mock_db.get = _get_category

    response = api_client.get(
        f"/categories/{category_id}",
        headers=gen_headers(is_admin),
    )
    assert response.status_code == 404


@pytest.mark.parametrize("is_admin", (True, False))
def test_get_category_correct(
    api_client: TestClient, mock_db: MagicMock, is_admin: bool
) -> None:
    mock_category = generate_random_db_category()

    def _get_product(_: Any, input_category_id: UUID) -> Category:
        assert input_category_id == mock_category.id
        return mock_category  # type: ignore[no-any-return]

    mock_db.get = _get_product

    response = api_client.get(
        f"/categories/{str(mock_category.id)}",
        headers=gen_headers(is_admin),
    )

    assert response.status_code == 200
    response_json = response.json()
    assert isinstance(response_json, dict)

    validate_category_response(response_json, mock_category)


def test_create_category_correct(api_client: TestClient, mock_db: MagicMock) -> None:
    category_data = generate_create_category_data()
    expected_categories = []

    def _add_category(category: Category) -> None:
        validate_db_category(category, category_data)

    def _db_refresh(category: Category) -> None:
        category.id = uuid4()  # type: ignore[assignment]
        expected_categories.append(category)

    mock_db.add = _add_category
    mock_db.refresh = _db_refresh

    response = api_client.post(
        "/categories/create", json=category_data, headers=gen_headers(True)
    )

    assert response.status_code == 201
    response_json = response.json()
    assert isinstance(response_json, dict)

    validate_category_response(response_json, expected_categories[0])


def test_create_category_forbidden(api_client: TestClient) -> None:
    category_data = generate_create_category_data()

    response = api_client.post(
        "/categories/create", json=category_data, headers=gen_headers(False)
    )
    assert response.status_code == 403


@pytest.mark.parametrize("field", ("name", "description"))
def test_create_category_missing_field(api_client: TestClient, field: str) -> None:
    category_data = generate_create_category_data()
    category_data.pop(field)

    response = api_client.post(
        "/categories/create", json=category_data, headers=gen_headers(True)
    )
    assert response.status_code == 422


def test_create_category_additional_field(api_client: TestClient) -> None:
    category_data = generate_create_category_data()
    category_data["additional"] = "abcd"

    response = api_client.post(
        "/categories/create", json=category_data, headers=gen_headers(True)
    )
    assert response.status_code == 422


def test_create_category_db_error(api_client: TestClient, mock_db: MagicMock) -> None:
    category_data = generate_create_category_data()

    mock_db.commit.side_effect = IntegrityError(
        statement="DB error", params=None, orig=BaseException("DB error\nVery serious")
    )

    response = api_client.post(
        "/categories/create", json=category_data, headers=gen_headers(True)
    )
    assert response.status_code == 400
    mock_db.rollback.assert_called_once()


def test_update_category_forbidden(api_client: TestClient) -> None:
    category_data = generate_create_category_data()

    response = api_client.patch(
        f"/categories/{str(uuid4())}",
        json=category_data,
        headers=gen_headers(False),
    )
    assert response.status_code == 403


@pytest.mark.parametrize("category_id", ("str", "123", str(uuid4()) + "a"))
def test_update_category_wrong_id(api_client: TestClient, category_id: str) -> None:
    update_data = generate_create_category_data()

    response = api_client.patch(
        f"/categories/{category_id}",
        json=update_data,
        headers=gen_headers(True),
    )
    assert response.status_code == 422


def test_update_category_not_found(api_client: TestClient, mock_db: MagicMock) -> None:
    category_id = str(uuid4())

    def _get_category(_: Any, input_category_id: UUID) -> None:
        assert str(input_category_id) == category_id
        return None

    mock_db.get = _get_category

    update_data = generate_create_category_data()

    response = api_client.patch(
        f"/categories/{category_id}",
        json=update_data,
        headers=gen_headers(True),
    )
    assert response.status_code == 404


def test_update_category_db_error(api_client: TestClient, mock_db: MagicMock) -> None:
    mock_category = generate_random_db_category()

    def _get_category(_: Any, category_id: str) -> Category:
        assert category_id == mock_category.id
        return mock_category  # type: ignore[no-any-return]

    mock_db.get = _get_category

    update_data = generate_create_category_data()

    mock_db.commit.side_effect = IntegrityError(
        statement="DB error", params=None, orig=BaseException("DB error\nVery serious")
    )

    response = api_client.patch(
        f"/categories/{str(mock_category.id)}",
        json=update_data,
        headers=gen_headers(True),
    )
    assert response.status_code == 400
    mock_db.rollback.assert_called_once()


def test_update_category_correct(api_client: TestClient, mock_db: MagicMock) -> None:
    mock_category = generate_random_db_category()
    orig_id = mock_category.id

    def _get_category(_: Any, category_id: str) -> Category:
        assert category_id == mock_category.id
        return mock_category  # type: ignore[no-any-return]

    mock_db.get = _get_category

    update_data = generate_create_category_data()

    response = api_client.patch(
        f"/categories/{str(mock_category.id)}",
        json=update_data,
        headers=gen_headers(True),
    )

    mock_db.commit.assert_called_once()
    assert mock_category.id == orig_id
    validate_db_category(mock_category, update_data)

    assert response.status_code == 200
    response_json = response.json()
    assert isinstance(response_json, dict)

    validate_category_response(response_json, mock_category)


def test_delete_category_forbidden(api_client: TestClient) -> None:
    response = api_client.delete(
        f"/categories/{str(uuid4())}", headers=gen_headers(False)
    )
    assert response.status_code == 403


@pytest.mark.parametrize("category_id", ("str", "123", str(uuid4()) + "a"))
def test_delete_category_wrong_id(api_client: TestClient, category_id: str) -> None:
    response = api_client.delete(
        f"/categories/{category_id}",
        headers=gen_headers(True),
    )
    assert response.status_code == 422


def test_delete_category_not_found(api_client: TestClient, mock_db: MagicMock) -> None:
    category_id = str(uuid4())

    def _get_category(_: Any, input_category_id: UUID) -> None:
        assert str(input_category_id) == category_id
        return None

    mock_db.get = _get_category

    response = api_client.delete(
        f"/categories/{category_id}",
        headers=gen_headers(True),
    )
    assert response.status_code == 404


def test_delete_category_correct(api_client: TestClient, mock_db: MagicMock) -> None:
    mock_category = generate_random_db_category()

    def _get_category(_: Any, category_id: str) -> Category:
        assert category_id == mock_category.id
        return mock_category  # type: ignore[no-any-return]

    def _delete_category(category: Category) -> None:
        assert category == mock_category

    mock_db.get = _get_category
    mock_db.delete = _delete_category

    response = api_client.delete(
        f"/categories/{str(mock_category.id)}",
        headers=gen_headers(True),
    )

    mock_db.commit.assert_called_once()
    assert response.status_code == 204
