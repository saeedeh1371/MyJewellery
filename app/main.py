from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, status

from app.repository import OrderRepository
from app.schemas import (
    BatchOrdersResponse,
    OrderRequest,
    OrderResponse,
    SummaryStatsResponse,
)
from app.services import OrderService

app = FastAPI(title="Order Service")

order_repository = OrderRepository()


def get_order_service() -> OrderService:
    """Provide an OrderService instance with the shared repository."""
    return OrderService(repository=order_repository)


OrderServiceDep = Annotated[OrderService, Depends(get_order_service)]


@app.post("/orders/batch", response_model=BatchOrdersResponse)
def ingest_orders(
    orders: list[OrderRequest], service: OrderServiceDep
) -> BatchOrdersResponse:
    """Validate, transform, and store a batch of orders."""
    return service.ingest_orders(orders=orders)


@app.get("/orders", response_model=list[OrderResponse])
def get_orders(
    service: OrderServiceDep,
    customer_id: str | None = None,
    min_total: float | None = Query(default=None, ge=0),
    max_total: float | None = Query(default=None, ge=0),
    category: str | None = None,
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[OrderResponse]:
    """Return orders filtered by optional query parameters."""
    if min_total is not None and max_total is not None and min_total > max_total:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="min_total cannot be greater than max_total",
        )
    return service.get_orders(
        customer_id=customer_id,
        min_total=min_total,
        max_total=max_total,
        category=category,
        limit=limit,
        offset=offset,
    )


@app.get("/stats/summary", response_model=SummaryStatsResponse)
def get_summary_stats(service: OrderServiceDep) -> SummaryStatsResponse:
    """Return aggregated statistics across all stored orders."""
    return service.get_summary_stats()
