from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Tuple

from patron_arby.common.order import Order

DEFAULT_NUMBER_PRECISION = 8


class ExchangeLimitationName(Enum):
    MIN_PRICE_STEP = "min_price_step"
    MIN_VOLUME_STEP = "min_volume_step"
    MIN_NOTIONAL = "min_notional"


class ExchangeLimitations(ABC):
    @abstractmethod
    def adjust_price_and_volume_to_market_requirements(self, order: Order):
        pass

    @abstractmethod
    def check_meets_exchange_filters(self, order: Order) -> Tuple[bool, Optional[str]]:
        pass
