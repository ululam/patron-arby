import logging
from typing import Dict

from patron_arby.common.bus import Bus
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
        order = self.converter.from_ws_event(event)
        order.event_raw_order = event
        self.order_dao.put_order(order)
