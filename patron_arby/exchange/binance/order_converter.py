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
            quantity=order_event.get(Binance.EVENT_KEY_QUANTITY),
            status=order_event.get(Binance.EVENT_KEY_ORDER_STATUS),
            order_id=order_event.get(Binance.EVENT_KEY_ORDER_ID))

        order.original_order = order_event

        return order

    def _get_client_order_id(self, order_event: Dict):
        client_order_id = order_event.get(Binance.EVENT_KEY_CLIENT_ORDER_ID)
        if not client_order_id or "_order_" not in client_order_id:
            # Order cancellation, or whatever, special case
            # https://github.com/binance-us/binance-official-api-docs/blob/master/user-data-stream.md#order-update
            return order_event.get(Binance.EVENT_KEY_ORIGINAL_CLIENT_ORDER_ID)
        return client_order_id
