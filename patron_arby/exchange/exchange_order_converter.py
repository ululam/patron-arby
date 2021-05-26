from abc import ABC, abstractmethod
from typing import Dict

from patron_arby.common.order import Order


class ExchangeOrderConverter(ABC):
    @abstractmethod
    def from_ws_event(self, order_event: Dict) -> Order:
        pass

    def from_rest_api_response(self, api_order: Dict) -> Order:
        pass
