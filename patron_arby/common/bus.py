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

    @property
    def positive_arbitrages_queue(self):
        return self._positive_arbitrages_queue

    @property
    def store_positive_arbitrages_queue(self):
        return self._store_positive_arbitrages_queue

    @property
    def fire_orders_queue(self):
        return self._fire_orders_queue

    @property
    def tickers_queue(self):
        return self._tickers_queue

    @property
    def all_arbitrages_queue(self):
        return self._all_arbitrages_queue
