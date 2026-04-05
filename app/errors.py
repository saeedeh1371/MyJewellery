from enum import Enum


class OrderErrorReason(str, Enum):
    DUPLICATE_ORDER_ID = "duplicate_order_id"
    EMPTY_ITEMS = "empty_items"
    INVALID_QUANTITY = "invalid_quantity"
    INVALID_UNIT_PRICE = "invalid_unit_price"
