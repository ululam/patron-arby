from queue import Queue


class Bus:
    """
    Communication bus between Arbitrage components
    Shared-mem implementation to be replaced by separate component (Redis most probably)
    """
    _arbitrage_findings_queue: Queue = Queue()
    _fire_orders_queue: Queue = Queue()
    _tickers_queue: Queue = Queue()

    @property
    def arbitrage_findings_queue(self):
        return self._arbitrage_findings_queue

    @property
    def fire_orders_queue(self):
        return self._fire_orders_queue

    @property
    def tickers_queue(self):
        return self._tickers_queue
