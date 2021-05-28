import logging
import threading
import time

from patron_arby.arbitrage.arby import PetroniusArbiter
from patron_arby.common.bus import Bus
from patron_arby.common.util import current_time_ms

log = logging.getLogger(__name__)


class ArbitrageThread(threading.Thread):

    def __init__(self, bus: Bus, arby: PetroniusArbiter) -> None:
        super().__init__()
        self.bus = bus
        self.arby = arby

    def run(self) -> None:
        # Wait some time for data to come
        time.sleep(3)

        exec_count = 0
        current_count = 0
        exec_time_sum = 0
        while True:
            ticker = self.bus.tickers_queue.get()

            start_time = current_time_ms()
            chains = self.arby.find({ticker.market})
            exec_time_sum += current_time_ms() - start_time

            self.bus.all_arbitrages_queue.put(chains)

            current_count += 1
            if current_count % 1000 == 0:
                exec_count += current_count
                log.info(f"Ran arbitrage {exec_count} times. Average execution time for last {current_count} "
                         f"invocations is {exec_time_sum/current_count} ms")
                exec_time_sum = 0
                current_count = 0
