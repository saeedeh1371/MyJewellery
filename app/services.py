from collections import defaultdict

from app.errors import OrderErrorReason
from app.repository import OrderRepository
from app.schemas import (
    BatchOrdersResponse,
    FailedOrder,
    Item,
    Order,
    OrderRequest,
    OrderResponse,
    SummaryStatsResponse,
)


class OrderService:
    """Handles order ingestion, querying, and aggregation logic."""

    def __init__(self, repository: OrderRepository) -> None:
        """Initialize the service with an order repository."""
        self.repository = repository

    def ingest_orders(self, orders: list[OrderRequest]) -> BatchOrdersResponse:
        """Validate, transform, and store a batch of orders."""
        failed_orders: list[FailedOrder] = []
        ingested_count = 0

        for order in orders:
            error_reason = self._validate_order(order=order)

            if error_reason is not None:
                failed_orders.append(
                    FailedOrder(
                        order_id=order.order_id,
                        reason=error_reason,
                    )
                )
                continue

            normalized_items = self._normalize_items(items=order.items)
            order_total = sum(
                item.quantity * item.unit_price for item in normalized_items
            )

            stored_order = Order(
                order_id=order.order_id,
                customer_id=order.customer_id,
                order_timestamp=order.order_timestamp,
                order_total=order_total,
                items=normalized_items,
            )

            self.repository.add_order(order=stored_order)
            ingested_count += 1

        return BatchOrdersResponse(
            ingested=ingested_count,
            failed=failed_orders,
        )

    def _validate_order(self, order: OrderRequest) -> OrderErrorReason | None:
        """Validate a single order against ingestion rules."""
        if self.repository.order_exists(order_id=order.order_id):
            return OrderErrorReason.DUPLICATE_ORDER_ID

        if not order.items:
            return OrderErrorReason.EMPTY_ITEMS

        for item in order.items:
            if item.quantity <= 0:
                return OrderErrorReason.INVALID_QUANTITY

            if item.unit_price < 0:
                return OrderErrorReason.INVALID_UNIT_PRICE

        return None

    def _normalize_items(self, items: list[Item]) -> list[Item]:
        """Return items with category values normalized to lowercase."""
        return [
            item.model_copy(update={"category": item.category.lower()})
            for item in items
        ]

    def get_orders(
        self,
        *,
        customer_id: str | None,
        min_total: float | None,
        max_total: float | None,
        category: str | None,
        limit: int,
        offset: int,
    ) -> list[OrderResponse]:
        """Return stored orders after applying optional filters and pagination."""

        normalized_category = category.lower() if category is not None else None

        filtered_orders = []

        for order in self.repository.get_orders():
            if customer_id is not None and order.customer_id != customer_id:
                continue

            if min_total is not None and order.order_total < min_total:
                continue

            if max_total is not None and order.order_total > max_total:
                continue

            if normalized_category is not None and not any(
                item.category == normalized_category for item in order.items
            ):
                continue

            filtered_orders.append(OrderResponse(**order.model_dump()))

        return filtered_orders[offset : offset + limit]

    def get_summary_stats(self) -> SummaryStatsResponse:
        """Return aggregated statistics across all stored orders."""
        orders = self.repository.get_orders()

        total_orders = len(orders)
        total_revenue = sum(order.order_total for order in orders)

        average_order_value = 0.0
        if total_orders > 0:
            average_order_value = round(total_revenue / total_orders, 2)

        orders_per_category: defaultdict[str, int] = defaultdict(int)
        revenue_per_category: defaultdict[str, float] = defaultdict(float)

        for order in orders:
            order_categories = {item.category for item in order.items}

            for category in order_categories:
                orders_per_category[category] += 1

            for item in order.items:
                revenue_per_category[item.category] += item.quantity * item.unit_price

        return SummaryStatsResponse(
            total_orders=total_orders,
            total_revenue=total_revenue,
            average_order_value=average_order_value,
            orders_per_category=orders_per_category,
            revenue_per_category=revenue_per_category,
        )
