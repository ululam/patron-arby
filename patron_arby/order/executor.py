import logging
import threading

from patron_arby.common.bus import Bus
from patron_arby.common.decorators import safely
from patron_arby.common.order import Order
from patron_arby.db.order_dao import OrderDao
from patron_arby.exchange.exchange_api import ExchangeApi

log = logging.getLogger(__name__)

SENTINEL_MESSAGE = "SHUTDOWN"

LOCK = threading.Lock()


# todo Refactor to async IO mode
# todo That will require async binance REST API impl
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
        try:
            result = self.exchange_api.put_order(o)
        except Exception as ex:
            # Add log line to identify which order failed
            log.error(f"Error placing order {o}: {ex}")
            self._remove_order_from_running(o)
            raise ex
        log.info(f"Got order result {result}")

    def run(self):
        log.debug("Starting")
        stop = False
        while not stop:
            msg = self.bus.fire_orders_queue.get(True)
            stop = self._process(msg)
        log.debug("Ending")

    @safely
    def _process(self, msg) -> bool:
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
        with LOCK:
            self.order_dao.put_order(order)

        return False

    def _remove_order_from_running(self, o: Order):
        chain_hash0 = o.client_order_id.split("_")[0]
        running_orders = self.bus.running_orders_storage[chain_hash0]
        if running_orders:
            running_orders.remove(o.client_order_id)

    def _on_sentinel(self):
        log.debug(f"Got {SENTINEL_MESSAGE}, stopping")
        # Re-send for others
        self.bus.fire_orders_queue.put(SENTINEL_MESSAGE)
        return True
