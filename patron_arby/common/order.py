from patron_arby.common.util import dict_from_obj


class Order:
    client_order_id: str
    order_side: str
    symbol: str
    quantity: float
    price: float

    def __init__(self, client_order_id: str, order_side: str, symbol: str, quantity: float, price: float) -> None:
        """
        :param client_order_id: Our trade client id
        :param order_side: BUY | SELL
        :param symbol: Trading pair symbol
        :param quantity:
        :param price:
        :return: Placed order dictionary
        """
        assert client_order_id is not None
        assert symbol is not None
        assert quantity is not None and quantity > 0
        assert price is not None and quantity > 0
        super().__init__()
        self.client_order_id = client_order_id
        self.order_side = order_side
        self.symbol = symbol
        self.quantity = quantity
        self.price = price

    def __str__(self) -> str:
        return dict_from_obj(self).__str__()
