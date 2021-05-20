from enum import Enum

DEFAULT_NUMBER_PRECISION = 8


class ExchangeLimitation(Enum):
    MIN_PRICE_STEP = "min_price_step"
    MIN_VOLUME_STEP = "min_volume_step"
