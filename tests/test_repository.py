from datetime import datetime, timezone

import pytest

from app.repository import OrderRepository
from app.schemas import Item, Order


@pytest.fixture
def order() -> Order:
    """Create a sample order for testing."""
    return Order(
        order_id="A1",
        customer_id="C1",
        order_timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
        order_total=20.0,
        items=[
            Item(sku="SKU1", quantity=2, unit_price=10.0, category="books"),
        ],
    )


def test_add_and_retrieve_order(order: Order) -> None:
    """Test that an added order can be retrieved by its ID."""
    repo = OrderRepository()

    repo.add_order(order)

    assert repo.get_order_by_id("A1") == order


def test_get_order_by_id_returns_none_for_missing() -> None:
    """Test that retrieving a non-existent order returns None."""
    repo = OrderRepository()

    assert repo.get_order_by_id("missing") is None


def test_order_exists(order: Order) -> None:
    """Test that order_exists correctly reports presence of an order."""
    repo = OrderRepository()

    assert repo.order_exists("A1") is False

    repo.add_order(order)

    assert repo.order_exists("A1") is True


def test_get_orders_returns_all(order: Order) -> None:
    """Test that get_orders returns all stored orders."""
    repo = OrderRepository()
    order2 = order.model_copy(update={"order_id": "A2"})

    repo.add_order(order)
    repo.add_order(order2)

    orders = repo.get_orders()
    assert len(orders) == 2
    assert {order.order_id for order in orders} == {"A1", "A2"}


def test_get_orders_empty() -> None:
    """Test that get_orders returns an empty list when no orders exist."""
    repo = OrderRepository()

    assert repo.get_orders() == []
