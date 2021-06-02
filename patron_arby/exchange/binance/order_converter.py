import logging
from typing import Dict, Optional

from patron_arby.common.order import Order, OrderSide
from patron_arby.exchange.binance.constants import Binance
from patron_arby.exchange.exchange_order_converter import ExchangeOrderConverter

log = logging.getLogger(__name__)


class BinanceOrderConverter(ExchangeOrderConverter):
    def from_ws_event(self, order_event: Dict) -> Order:
        order = Order(
            client_order_id=self._get_client_order_id_from_ws(order_event),
            order_side=OrderSide[order_event.get(Binance.EVENT_KEY_ORDER_SIDE)],
            symbol=order_event.get(Binance.EVENT_KEY_SYMBOL),
            price=order_event.get(Binance.EVENT_KEY_PRICE),
            quantity=order_event.get(Binance.EVENT_KEY_QUANTITY),
            status=order_event.get(Binance.EVENT_KEY_ORDER_STATUS),
            order_id=order_event.get(Binance.EVENT_KEY_ORDER_ID)
        )
        order.arbitrage_hash8 = self.get_arbitrage_hash8_from_client_order_id(order.client_order_id)
        order.rest_reply_raw_order = order_event
        return order

    def from_rest_api_response(self, api_order: Dict) -> Order:
        order = Order(
            client_order_id=api_order.get(Binance.REST_KEY_CLIENT_ORDER_ID),
            order_side=OrderSide[api_order.get(Binance.REST_KEY_SIDE)],
            symbol=api_order.get(Binance.REST_KEY_SYMBOL),
            price=api_order.get(Binance.REST_KEY_PRICE),
            quantity=api_order.get(Binance.REST_KEY_ORIG_QUANTITY),
            status=api_order.get(Binance.REST_KEY_STATUS),
            order_id=api_order.get(Binance.REST_KEY_ORDER_ID),
            transaction_time=api_order.get(Binance.REST_KEY_TRANSACT_TIME)
        )
        order.arbitrage_hash8 = self.get_arbitrage_hash8_from_client_order_id(order.client_order_id)
        order.rest_reply_raw_order = api_order
        return order

    @staticmethod
    def _get_client_order_id_from_ws(order_event: Dict) -> str:
        client_order_id = order_event.get(Binance.EVENT_KEY_CLIENT_ORDER_ID)
        if not client_order_id or "_order_" not in client_order_id:
            # Order cancellation, or whatever, special case
            # https://github.com/binance-us/binance-official-api-docs/blob/master/user-data-stream.md#order-update
            return order_event.get(Binance.EVENT_KEY_ORIGINAL_CLIENT_ORDER_ID)
        return client_order_id

    # noinspection PyBroadException
    @staticmethod
    def get_arbitrage_hash8_from_client_order_id(client_order_id: str) -> Optional[int]:
        if not client_order_id:
            return None
        try:
            return int(client_order_id.split("_")[0])   # we suggest to have "12345678_order_1" client_order_id format
        except Exception as ex:
            log.warning(f"Cannot get arbitrage hash8 from client order_id '{client_order_id}': {ex}")
            return None
