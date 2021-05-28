from dataclasses import dataclass

from patron_arby.common.util import current_time_ms


@dataclass
class Ticker:
    market: str
    best_bid: float
    best_bid_quantity: float
    best_ask: float
    best_ask_quantity: float
    time_ms: int = -1

    def __post_init__(self):
        if self.time_ms == -1:
            self.time_ms = current_time_ms()
