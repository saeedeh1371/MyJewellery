# Order Service

A FastAPI service that ingests order data, validates and transforms it, stores it in memory, and exposes endpoints to retrieve and aggregate the data.

## Setup

### Prerequisites

- Python 3.12+

### Installation

```bash
python -m venv venv
source venv/bin/activate
pip install ".[dev]"
```

## Running the Service

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

Interactive API docs are available at `http://127.0.0.1:8000/docs`.

## Running Tests

```bash
python -m pytest tests/ -v
```

## API Endpoints

| Method | Path              | Description                              |
|--------|-------------------|------------------------------------------|
| POST   | `/orders/batch`   | Ingest a batch of orders                 |
| GET    | `/orders`         | Query orders with optional filters       |
| GET    | `/stats/summary`  | Get aggregated statistics across orders  |

### Query Parameters for `GET /orders`

| Param         | Type   | Description                                  |
|---------------|--------|----------------------------------------------|
| `customer_id` | string | Filter by customer                           |
| `min_total`   | float  | Orders with total >= value (must be >= 0)    |
| `max_total`   | float  | Orders with total <= value (must be >= 0)    |
| `category`    | string | Orders with at least one item in category    |
| `limit`       | int    | Page size (1-200, default: 100)              |
| `offset`      | int    | Number of records to skip (default: 0)       |

## Design Decisions

- **Layered architecture**: The code is split into routing (`main.py`), business logic (`services.py`), data access (`repository.py`), and data models (`schemas.py`). This separation makes each layer independently testable and easy to reason about.

- **Schema separation**: Models are organized into three categories — internal models (`Order`, `Item`) used by the repository and service layers, request models (`OrderRequest`) for API input, and response models (`OrderResponse`, `BatchOrdersResponse`, etc.) for API output. Response models inherit from internal models where possible to avoid duplication.

- **Dependency injection**: `OrderService` is injected into endpoints via FastAPI's `Depends` system, making it straightforward to swap dependencies for testing.

- **Validation in the service layer**: Order validation (duplicate IDs, empty items, invalid quantities/prices) is handled in the service rather than via Pydantic field constraints. This allows the batch endpoint to process all orders and report individual failures with descriptive reasons, rather than rejecting the entire request on the first error.

- **Error reasons as an enum**: `OrderErrorReason` uses a string enum to provide consistent, machine-readable error reasons in the batch response.

- **Category normalization**: Categories are normalized to lowercase during ingestion and category filtering is case-insensitive.

- **Single-pass filtering**: `get_orders` uses a single loop with `continue` statements to apply all filters, avoiding multiple passes over the data.

- **Query parameter validation**: `min_total` and `max_total` are constrained to non-negative values, `limit` is capped at 200, and a 400 error is returned if `min_total` exceeds `max_total`.

## Assumptions

- Orders are uniquely identified by `order_id`. Submitting an order with an existing `order_id` is treated as a duplicate and rejected.
- Validation is fail-fast per order: only the first validation error is reported for each order.
- `orders_per_category` counts each order once per category, even if the order contains multiple items in the same category.
- `limit` and `offset` are constrained (`limit`: 1-200, `offset`: >= 0) to prevent excessively large responses and mimic production API behavior. This constraint was not specified in the requirements but was added as a safeguard.
- `min_total` must be less than or equal to `max_total` when both are provided; otherwise a 400 error is returned.
- The service uses in-memory storage; all data is lost when the service restarts.
