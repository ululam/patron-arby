import logging
from typing import Dict

from patron_arby.common.bus import Bus
from patron_arby.common.util import current_time_ms
from patron_arby.config.base import ARBITRAGE_COINS
from patron_arby.exchange.binance.ticker_converter import BinanceTickerConverter
from patron_arby.exchange.exchange_event_listener import ExchangeEventListener

log = logging.getLogger(__name__)


class ArbitrageEventListener(ExchangeEventListener):
    start_time = 0
    counter = 0
    total_counter = 0

    def __init__(self, bus: Bus) -> None:
        super().__init__()
        self.bus = bus
        self.ticker_converter = BinanceTickerConverter()
        self.all_possible_tickers = set()
        coins = [c.lower() for c in ARBITRAGE_COINS]
        for c1 in coins:
            for c2 in coins:
                if c1 == c2:
                    continue
                self.all_possible_tickers.add(c1 + c2)

    def on_exchange_event(self, event: Dict):
        if self.counter == 0:
            self.start_time = current_time_ms()

        stream = event.get("stream")
        if not stream:
            return
        ticker = stream.split("@")[0]
        if ticker not in self.all_possible_tickers:
            return

        self.bus.tickers_queue.put(
            self.ticker_converter.from_ws_event(event)
        )

        self.counter += 1
        time_passed = current_time_ms() - self.start_time
        if time_passed > 10_000:
            events_per_second = 1_000 * self.counter / time_passed
            self.total_counter += self.counter
            log.debug(f"Ticker updates for our coins, per second: {int(events_per_second)}")
            log.debug(f"Total ticker updates for our coins, since start: {self.total_counter}")
            self.counter = 0
