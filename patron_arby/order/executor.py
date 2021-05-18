import logging
import threading

from patron_arby.common.bus import Bus
from patron_arby.common.decorators import safely
from patron_arby.common.order import Order
from patron_arby.db.order_dao import OrderDao
from patron_arby.exchange.exchange_api import ExchangeApi

log = logging.getLogger(__name__)

SENTINEL_MESSAGE = "SHUTDOWN"


# todo Refactor to async IO mode
class OrderExecutor(threading.Thread):
    def __init__(self, bus: Bus, exchange_api: ExchangeApi, order_dao: OrderDao) -> None:
        """
        :param bus: Message bus
        :param exchange_api:  ExchangeApi. Be careful, and create 1 API instance per thread if its not thread-safe
        """
        super().__init__()
        self.bus = bus
        self.exchange_api = exchange_api
        self.order_dao = order_dao

    def _post_order(self, o: Order):
        log.info(f"Placing order {o}")
        result = self.exchange_api.put_order(o)
        log.info(f"Got order result {result}")

    def run(self):
        log.debug("Starting")
        stop = False
        while not stop:
            msg = self.bus.fire_orders_queue.get(True)
            stop = self._process(msg)
        log.debug("Ending")

    @safely
    def _process(self, msg):
        if msg == SENTINEL_MESSAGE:
            return self._on_sentinel()

        if not isinstance(msg, Order):
            log.error(f"Message should be either of type {Order} or == '{SENTINEL_MESSAGE}' for quit. "
                      f"Got {msg}, skipping")
            return False

        order: Order = msg
        # Fire first
        self._post_order(order)
        # Then, save.
        # todo Possible race condition (if we got a status update from exchange BEFORE or DURING next line
        # invocation. Highly improbable, but still possible
        # self.order_dao.put_order(order)

        return False

    def _on_sentinel(self):
        log.debug(f"Got {SENTINEL_MESSAGE}, stopping")
        # Re-send for others
        self.bus.fire_orders_queue.put(SENTINEL_MESSAGE)
        return True
