import logging
import time
from threading import Thread

from patron_arby.common.decorators import safely
from patron_arby.common.order import Order
from patron_arby.common.util import current_time_ms
from patron_arby.config.base import (
    ORDER_CANCELATOR_ORDER_TTL_MS,
    ORDER_CANCELATOR_RUN_PERIOD_MS,
)
from patron_arby.exchange.exchange_api import ExchangeApi

log = logging.getLogger(__name__)


class OrderCancelator(Thread):
    def __init__(self, exchange_api: ExchangeApi, order_ttl_ms: int = ORDER_CANCELATOR_ORDER_TTL_MS) -> None:
        super().__init__()
        self.exchange_api = exchange_api
        self.order_ttl_ms = order_ttl_ms

    def run(self) -> None:
        log.info(f"Running with order TTL = {self.order_ttl_ms} ms")
        while True:
            time.sleep(ORDER_CANCELATOR_RUN_PERIOD_MS * 0.001)
            self._do_run()

    @safely
    def _do_run(self):
        open_orders = self.exchange_api.get_open_orders()
        our_open_orders = [o for o in open_orders if o.is_our_order()]
        orders_to_cancel = [o for o in our_open_orders if (current_time_ms() - o.created_at) > self.order_ttl_ms]
        if len(orders_to_cancel) == 0:
            return

        log.info(f"Got {len(orders_to_cancel)} orders to cancel")
        for o in orders_to_cancel:
            self._cancel_order(o)

    @safely
    def _cancel_order(self, o: Order):
        self.exchange_api.cancel_order(symbol=o.symbol, order_id=o.order_id)
