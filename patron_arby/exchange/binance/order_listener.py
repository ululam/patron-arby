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
        order = self.converter.from_ws_event(event)
        if not order.is_our_order():
            log.warning(f"Not out order, ignoring: {order}")
            return

        if self._check_that_event_order_is_older_than_last_update(order):
            self.order_dao.put_order(order)

    def _check_that_event_order_is_older_than_last_update(self, order: Order) -> bool:
        existing_order = self.order_dao.get_order(order.client_order_id)
        if not existing_order:
            # https://linear.app/good-it-works/issue/ACT-446
            log.warning(f"Order does not exist for client_order_id {order.client_order_id}. Most probably we got the "
                        f"event BEFORE we got REST API `put_order` response and wrote its result to he database. "
                        f"Ignoring event.")
            return False

        event_time_ms = order.event_raw_order.get(Binance.EVENT_KEY_EVENT_TIME)
        if not event_time_ms:
            log.warning(f"Unable to get even time from event, ignoring event: {order.event_raw_order}")
            return False

        transact_time = existing_order.transaction_time if existing_order.transaction_time else 0
        last_event_time = existing_order.event_raw_order.get(Binance.EVENT_KEY_EVENT_TIME) if \
            existing_order.event_raw_order else 0

        if event_time_ms > max(transact_time, last_event_time):
            return True

        log.info("Got order event 'from the past'. The data we have is more recent than event")

        # Now, check if we should put his event as `event_raw_order` field value (its newer than that field contents)
        if event_time_ms > last_event_time:
            existing_order.event_raw_order = order.event_raw_order
            self.order_dao.put_order(existing_order)

        return False
