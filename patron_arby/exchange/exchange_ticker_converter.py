from abc import ABC, abstractmethod
from typing import Dict

from patron_arby.common.ticker import Ticker


class ExchangeTickerConverter(ABC):
    @abstractmethod
    def from_ws_event(self, order_event: Dict) -> Ticker:
        pass
