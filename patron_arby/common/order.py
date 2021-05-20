from dataclasses import dataclass
from enum import Enum
from typing import Dict

from patron_arby.common.util import current_time_ms, dict_from_obj, obj_from_dict


class OrderSide(Enum):
    SELL = "SELL"
    BUY = "BUY"

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.__str__()


@dataclass(eq=True)
class Order:
    client_order_id: str
    order_side: OrderSide
    symbol: str
    quantity: float
    price: float
    created_at: int = current_time_ms()
    updated_at: int = 0
    original_order: Dict = None
    arbitrage_id: str = None
    exchange: str = "Binance"
    status: str = None

    def __init__(self, client_order_id: str, order_side: OrderSide, symbol: str, price: float, quantity: float) -> None:
        """
        :param client_order_id: Our trade client id
        :param order_side: BUY | SELL
        :param symbol: Trading pair symbol
        :param volume:
        :param price:
        :return: Placed order dictionary
        """
        super().__init__()
        self.client_order_id = client_order_id
        self.order_side = order_side
        self.symbol = symbol
        self.quantity = quantity
        self.price = price

    def __str__(self) -> str:
        return dict_from_obj(self).__str__()

    def is_buy(self) -> bool:
        return self.order_side == OrderSide.BUY

    def to_dict(self):
        d = dict_from_obj(self)
        d["order_side"] = self.order_side.name if self.order_side else None
        return d

    @staticmethod
    def from_dict(order_dict: Dict):
        o = obj_from_dict(order_dict, Order(None, None, "", 0, 0))
        o.order_side = OrderSide[o.order_side] if o.order_side else None
        return o
