from queue import Queue


class Bus:
    """
    Communication bus between Arbitrage components
    Shared-mem implementation to be replaced by separate component (Redis most probably)
    """
    _positive_arbitrages_queue: Queue = Queue()
    _store_positive_arbitrages_queue: Queue = Queue()
    _fire_orders_queue: Queue = Queue()
    _tickers_queue: Queue = Queue()
    _all_arbitrages_queue: Queue = Queue()

    # When set to True, all trading activities are ceased
    _stop_trading = False

    @property
    def positive_arbitrages_queue(self) -> Queue:
        return self._positive_arbitrages_queue

    @property
    def store_positive_arbitrages_queue(self) -> Queue:
        return self._store_positive_arbitrages_queue

    @property
    def fire_orders_queue(self) -> Queue:
        return self._fire_orders_queue

    @property
    def tickers_queue(self) -> Queue:
        return self._tickers_queue

    @property
    def all_arbitrages_queue(self) -> Queue:
        return self._all_arbitrages_queue

    @property
    def is_stop_trading(self) -> bool:
        return self._stop_trading

    def set_stop_trading(self, stop_trading: bool):
        self._stop_trading = stop_trading
