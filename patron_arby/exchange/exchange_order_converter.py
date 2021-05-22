from abc import ABC, abstractmethod
from typing import Dict

from patron_arby.common.order import Order


class ExchangeOrderConverter(ABC):
    @abstractmethod
    def convert(self, order_event: Dict) -> Order:
        pass
