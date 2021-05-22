import logging
from typing import Dict

from patron_arby.common.bus import Bus
from patron_arby.common.order import Order
from patron_arby.db.order_dao import OrderDao
from patron_arby.exchange.binance.constants import Binance
from patron_arby.exchange.binance.order_converter import BinanceOrderConverter
from patron_arby.exchange.exchange_event_listener import ExchangeEventListener

log = logging.getLogger(__name__)


class BinanceOrderListener(ExchangeEventListener):
    def __init__(self, bus: Bus, order_dao: OrderDao) -> None:
        super().__init__()
        self.bus = Bus
        self.order_dao = order_dao
        self.converter = BinanceOrderConverter()

    def on_exchange_event(self, event: Dict):
        if event.get(Binance.EVENT_KEY_TYPE) != "executionReport":
            return

        log.debug(f"Got order event {event}")

        order = self.converter.convert(event)

        log.info(f"Got notification that order {order.client_order_id} changed to status {order.status}")

        self.order_dao.put_order(order)

        if order.status == Binance.ORDER_STATUS_FILLED:
            self.on_order_executed(order)

    def on_order_executed(self, order: Order):
        # Not a super solution, but there's a strong hope we won't run into hundreds of running arbitrage chains
        chain_hash0 = order.client_order_id.split("_")[0]
        running_order_ids = self.bus.running_orders_storage[chain_hash0]
        if running_order_ids:
            running_order_ids.remove(order.client_order_id)
