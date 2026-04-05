from app.schemas import Order


class OrderRepository:
    """
    In-memory repository for storing and retrieving orders.

    This class acts as the data access layer of the application.
    It stores orders in a dictionary keyed by `order_id`,
    where each value is a processed `Order`.
    """

    def __init__(self) -> None:
        self.orders_by_id: dict[str, Order] = {}

    def add_order(self, order: Order) -> None:
        """
        Store a new order.
        """
        self.orders_by_id[order.order_id] = order

    def get_order_by_id(self, order_id: str) -> Order | None:
        """
        Retrieve a single order by its ID.
        Returns the corresponding Order if found, otherwise None.
        """
        return self.orders_by_id.get(order_id)

    def get_orders(self) -> list[Order]:
        """
        Retrieve a list of all stored orders.
        """
        return list(self.orders_by_id.values())

    def order_exists(self, order_id: str) -> bool:
        """
        Check if an order with the given ID already exists.
        Returns true if the order exists, otherwise false.
        """
        return order_id in self.orders_by_id
