import logging
import threading

from patron_arby.arbitrage.market_data import MarketData
from patron_arby.common.bus import Bus
from patron_arby.common.decorators import safely
from patron_arby.common.order import Order
from patron_arby.common.util import current_time_ms
from patron_arby.db.order_dao import OrderDao
from patron_arby.exchange.binance.balances_checker import BalancesChecker
from patron_arby.exchange.exchange_api import ExchangeApi

log = logging.getLogger(__name__)

SENTINEL_MESSAGE = "SHUTDOWN"


# todo Refactor to async IO mode
# todo That will require async binance REST API impl
class OrderExecutor(threading.Thread):
    def __init__(self, bus: Bus, exchange_api: ExchangeApi, order_dao: OrderDao,
                 market_data: MarketData = None,
                 balances_checker: BalancesChecker = None) -> None:
        """
        :param bus: Message bus
        :param exchange_api:  ExchangeApi. Be careful, and create 1 API instance per thread if its not thread-safe
        """
        super().__init__()
        self.bus = bus
        self.exchange_api = exchange_api
        self.order_dao = order_dao
        self.market_data = market_data
        self.balances_checker = balances_checker

    def _post_order(self, o: Order) -> Order:
        log.info(f"Placing order {o.client_order_id}")
        # Set fire time for statistics
        o.fired_at = current_time_ms()
        try:
            result_order = self.exchange_api.put_order(o)
        except Exception as ex:
            # Add log line to identify which order failed
            log.error(f"Error placing order {o}: {ex}")
            self._print_extra_info_for_exception(ex)
            o.status = "ERROR"
            o.comment = f"{ex}"
            return o
        # Preserve correct times
        result_order.created_at = o.created_at
        result_order.fired_at = o.fired_at
        log.debug(f"Placed order: {result_order}")
        return result_order

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
        # todo
        self._print_ticker_info(order)
        result_order = self._post_order(order)
        # Then, save.
        self.order_dao.put_order(result_order)

        return False

    def _print_ticker_info(self, order: Order):
        if not self.market_data:
            return
        ticker = self.market_data.get_ticker(order.symbol)
        log.debug(f"Current ticker info for order_client_id {order.client_order_id}: {ticker}")

    def _print_extra_info_for_exception(self, ex: Exception):
        if not self.balances_checker:
            return
        if hasattr(ex, "code"):
            print(f"Has code: {ex.code}")
            # APIError(code=-2010) Insufficient balance => print balances
            if str(ex.code) == "-2010":
                if self.balances_checker:
                    self.balances_checker.log_balances()

    def _on_sentinel(self):
        log.debug(f"Got {SENTINEL_MESSAGE}, stopping")
        # Re-send for others
        self.bus.fire_orders_queue.put(SENTINEL_MESSAGE)
        return True
