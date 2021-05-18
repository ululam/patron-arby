from typing import Dict

from patron_arby.common.order import Order
from patron_arby.exchange.binance.constants import Binance
from patron_arby.exchange.exchange_order_converter import ExchangeOrderConverter


class BinanceOrderConverter(ExchangeOrderConverter):
    def convert(self, order_event: Dict) -> Order:
        order = Order(client_order_id=order_event.get(Binance.EVENT_KEY_CLIENT_ORDER_ID),
            order_side=order_event.get(Binance.EVENT_KEY_ORDER_SIDE),
            symbol=order_event.get(Binance.EVENT_KEY_SYMBOL),
            price=order_event.get(Binance.EVENT_KEY_PRICE),
            quantity=order_event.get(Binance.EVENT_KEY_QUANTITY))

        order.original_order = order_event

        return order
