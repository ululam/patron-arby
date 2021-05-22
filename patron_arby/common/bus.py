from queue import Queue
from typing import Dict, Set


class Bus:
    """
    Communication bus between Arbitrage components
    Shared-mem implementation to be replaced by separate component (Redis most probably)
    """
    _arbitrage_findings_queue: Queue = Queue()
    _fire_orders_queue: Queue = Queue()
    # Dict of [chain -> List of running orders.
    # Is promised to be thread-safe (if GIL)
    # https://docs.python.org/3/glossary.html#term-global-interpreter-lock
    # todo If running in containers, think how to provide similar 1-ms-digit communication channel (Redis most probably)
    _running_orders_storage: Dict[str, Set[str]] = dict()

    @property
    def arbitrage_findings_queue(self):
        return self._arbitrage_findings_queue

    @property
    def fire_orders_queue(self):
        return self._fire_orders_queue

    @property
    def running_orders_storage(self) -> Dict[str, Set[str]]:
        return self._running_orders_storage
