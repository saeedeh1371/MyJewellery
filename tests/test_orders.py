from collections.abc import Generator
from uuid import uuid4

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.errors import OrderErrorReason
from app.main import app, order_repository

client = TestClient(app)


def build_item_payload(**overrides) -> dict:
    """Build a valid item payload for tests."""
    return {
        "sku": "SKU1",
        "quantity": 1,
        "unit_price": 10.0,
        "category": "Books",
        **overrides,
    }


def build_order_payload(**overrides) -> dict:
    """Build a valid order payload with sensible defaults for tests."""
    return {
        "order_id": str(uuid4()),
        "customer_id": "C1",
        "order_timestamp": "2024-01-01T10:00:00Z",
        "items": [build_item_payload()],
        "currency": "EUR",
        **overrides,
    }


@pytest.fixture(autouse=True)
def clear_repository() -> Generator[None, None, None]:
    """
    Reset the in-memory order repository before each test.

    Ensures test isolation since the repository is shared across requests.
    """
    order_repository.orders_by_id.clear()
    yield


# -------------------
# Ingestion Tests
# -------------------


def test_ingest_orders_successfully() -> None:
    """Test that a valid order is ingested successfully with no failures."""
    payload = [build_order_payload()]

    response = client.post("/orders/batch", json=payload)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "ingested": 1,
        "failed": [],
    }


def test_reject_empty_items() -> None:
    """Test that an order with an empty items list is rejected."""
    payload = [build_order_payload(items=[])]

    response = client.post("/orders/batch", json=payload)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["ingested"] == 0
    assert response.json()["failed"][0]["reason"] == OrderErrorReason.EMPTY_ITEMS


def test_reject_invalid_quantity() -> None:
    """Test that an order with a non-positive quantity is rejected."""
    payload = [build_order_payload(items=[build_item_payload(quantity=-1)])]

    response = client.post("/orders/batch", json=payload)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["failed"][0]["reason"] == OrderErrorReason.INVALID_QUANTITY


def test_reject_invalid_unit_price() -> None:
    """Test that an order with a negative unit price is rejected."""
    payload = [build_order_payload(items=[build_item_payload(unit_price=-5.0)])]

    response = client.post("/orders/batch", json=payload)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["failed"][0]["reason"] == OrderErrorReason.INVALID_UNIT_PRICE


def test_reject_duplicate_order_id() -> None:
    """Test that an order with an already existing order_id is rejected."""
    order_id = str(uuid4())
    payload = [build_order_payload(order_id=order_id)]

    client.post("/orders/batch", json=payload)
    response = client.post("/orders/batch", json=payload)

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["failed"][0]["reason"] == OrderErrorReason.DUPLICATE_ORDER_ID


# -------------------
# Query Tests
# -------------------


def test_get_orders_with_filters() -> None:
    """Test that orders can be filtered by customer_id."""
    payload = [
        build_order_payload(customer_id="C1"),
        build_order_payload(customer_id="C2"),
    ]

    client.post("/orders/batch", json=payload)

    response = client.get("/orders", params={"customer_id": "C1"})

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 1
    assert response.json()[0]["customer_id"] == "C1"


def test_get_orders_with_category_filter_case_insensitive() -> None:
    """Test that category filtering is case-insensitive."""
    payload = [build_order_payload(items=[build_item_payload(category="Books")])]

    client.post("/orders/batch", json=payload)

    response = client.get("/orders", params={"category": "books"})

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 1


def test_get_orders_with_min_max_total_filter() -> None:
    """Test that orders can be filtered by min_total and max_total."""
    mid_order_id = str(uuid4())
    payload = [
        build_order_payload(items=[build_item_payload(unit_price=10.0)]),
        build_order_payload(
            order_id=mid_order_id, items=[build_item_payload(unit_price=50.0)]
        ),
        build_order_payload(items=[build_item_payload(unit_price=100.0)]),
    ]

    client.post("/orders/batch", json=payload)

    response = client.get("/orders", params={"min_total": 25, "max_total": 75})

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 1
    assert response.json()[0]["order_id"] == mid_order_id


def test_pagination_limit_and_offset() -> None:
    """Test that limit and offset correctly paginate results."""
    order_ids = [str(uuid4()) for _ in range(10)]
    payload = [build_order_payload(order_id=order_id) for order_id in order_ids]

    client.post("/orders/batch", json=payload)

    response = client.get("/orders", params={"limit": 3, "offset": 2})

    assert response.status_code == status.HTTP_200_OK
    assert len(response.json()) == 3
    returned_ids = [order["order_id"] for order in response.json()]
    assert returned_ids == order_ids[2:5]


# -------------------
# Stats Tests
# -------------------


def test_summary_stats_correctness() -> None:
    """Test that summary statistics are correctly aggregated across orders."""
    payload = [
        build_order_payload(
            items=[
                build_item_payload(
                    sku="S1", quantity=2, unit_price=10.0, category="Books"
                ),
                build_item_payload(
                    sku="S2", quantity=1, unit_price=30.0, category="Electronics"
                ),
            ],
        ),
        build_order_payload(
            customer_id="C2",
            items=[
                build_item_payload(
                    sku="S3", quantity=1, unit_price=20.0, category="Books"
                ),
            ],
        ),
    ]

    client.post("/orders/batch", json=payload)

    response = client.get("/stats/summary")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "total_orders": 2,
        "total_revenue": 70.0,
        "average_order_value": 35.0,
        "orders_per_category": {
            "books": 2,
            "electronics": 1,
        },
        "revenue_per_category": {
            "books": 40.0,
            "electronics": 30.0,
        },
    }


def test_summary_stats_empty() -> None:
    """Test that summary statistics return zeros when no orders exist."""
    response = client.get("/stats/summary")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        "total_orders": 0,
        "total_revenue": 0.0,
        "average_order_value": 0.0,
        "orders_per_category": {},
        "revenue_per_category": {},
    }
