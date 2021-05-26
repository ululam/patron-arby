from dataclasses import dataclass

from patron_arby.common.util import current_time_ms


@dataclass
class Ticker:
    market: str
    best_bid: float
    best_bid_quantity: float
    best_ask: float
    best_ask_quantity: float
    time_ms: int = current_time_ms()
