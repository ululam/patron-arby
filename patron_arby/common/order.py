from dataclasses import dataclass
from enum import Enum
from typing import Dict

from patron_arby.common.util import current_time_ms, dict_from_obj, obj_from_dict
from patron_arby.exchange.binance.constants import Binance


class OrderSide(Enum):
    SELL = "SELL"
    BUY = "BUY"

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.__str__()


@dataclass(eq=True)
class Order:
    # Consists of chain.hash8() + "_order_" + number of the order, e.g. "349dsafa_order_2"
    client_order_id: str
    order_side: OrderSide
    symbol: str
    quantity: float
    price: float
    created_at: int = -1
    updated_at: int = 0
    fired_at: int = 0
    arbitrage_hash8: int = None
    rest_reply_raw_order: Dict = None
    event_raw_order: Dict = None
    exchange: str = Binance.NAME
    status: str = "NEW"
    order_id: str = None
    transaction_time: int = -1
    comment: str = ""

    def __post_init__(self):
        if self.created_at == -1:
            self.created_at = current_time_ms()

    def is_buy(self) -> bool:
        return self.order_side == OrderSide.BUY

    def is_our_order(self):
        return "_order_" in self.client_order_id

    def to_dict(self):
        d = dict_from_obj(self)
        d["order_side"] = str(self.order_side) if self.order_side else None
        # Remove keys for None values explicitly
        return {k: v for k, v in d.items() if v is not None}

    @staticmethod
    def from_dict(order_dict: Dict):
        o = obj_from_dict(order_dict, Order(None, None, "", price=0, quantity=0))
        o.order_side = OrderSide[o.order_side] if o.order_side else None
        return o

    def get_what_we_propose_volume(self) -> float:
        """
        :return: Volume of the coin which we actually spend in this step
        """
        return self.quantity * self.price if self.is_buy() else self.quantity
