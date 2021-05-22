import abc
from abc import ABC
from typing import Dict


class ExchangeEventListener(ABC):
    @abc.abstractmethod
    def on_exchange_event(self, event: Dict):
        pass
