from datetime import datetime

from pydantic import BaseModel

from app.errors import OrderErrorReason

# -------------------
# Internal Models
# -------------------


class Item(BaseModel):
    """Represents a single item within an order."""

    sku: str
    quantity: int
    unit_price: float
    category: str


class Order(BaseModel):
    """Represents a processed order stored in the repository."""

    order_id: str
    customer_id: str
    order_timestamp: datetime
    order_total: float
    items: list[Item]


# -------------------
# Request Models
# -------------------


class OrderRequest(BaseModel):
    """Represents an incoming order payload."""

    order_id: str
    customer_id: str
    order_timestamp: datetime
    items: list[Item]
    currency: str


# -------------------
# Response Models
# -------------------


class FailedOrder(BaseModel):
    """Represents an order that failed validation during batch ingestion."""

    order_id: str
    reason: OrderErrorReason


class BatchOrdersResponse(BaseModel):
    """Response returned after processing a batch of orders."""

    ingested: int
    failed: list[FailedOrder]


class OrderResponse(Order):
    """Represents a processed order returned by the API."""


class SummaryStatsResponse(BaseModel):
    """Aggregated statistics across all stored orders."""

    total_orders: int
    total_revenue: float
    average_order_value: float
    orders_per_category: dict[str, int]
    revenue_per_category: dict[str, float]
