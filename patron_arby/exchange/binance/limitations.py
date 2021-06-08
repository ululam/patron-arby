import logging
from decimal import Decimal
from typing import Dict, Optional, Tuple, Union

from patron_arby.common.order import Order
from patron_arby.common.util import to_decimal
from patron_arby.exchange.exchange_limitations import (
    ExchangeLimitationName,
    ExchangeLimitations,
)

log = logging.getLogger(__name__)


class BinanceExchangeLimitations(ExchangeLimitations):
    limits: Dict[str, Dict[ExchangeLimitationName, float]] = dict()

    def __init__(self, binance_exchange_info: Dict) -> None:
        super().__init__()
        self._build_exchange_limitations(binance_exchange_info)

    def get_limitations(self) -> Dict[str, Dict[ExchangeLimitationName, float]]:
        return self.limits

    def adjust_price_and_volume_to_market_requirements(self, order: Order):
        symbol_limits = self.limits.get(order.symbol)
        if not symbol_limits:
            log.fine(f"Limits for {order.symbol} not found")
            return order

        min_price_step = symbol_limits.get(ExchangeLimitationName.MIN_PRICE_STEP)
        if min_price_step:
            order.price = to_decimal(order.price, Decimal(str(min_price_step)))

        min_volume_step = symbol_limits.get(ExchangeLimitationName.MIN_VOLUME_STEP)
        if min_volume_step:
            order.quantity = to_decimal(order.quantity, Decimal(str(min_volume_step)))

        return order

    def check_meets_exchange_filters(self, order: Order) -> Tuple[bool, Optional[str]]:
        meets_notional, message = self._meets_min_notional(order)
        if not meets_notional:
            # If min min_notional is not met, put no orders
            return False, f"Order does not meet MIN_NOTIONAL filter: ({message})"
        return meets_notional, message

    def _meets_min_notional(self, order: Order) -> Tuple[bool, Optional[str]]:
        """
        :param order:
        :return: True if order volume meets MIN_NOTIONAL exchange requirement, or if no MIN_NOTIONAL set.
        If MIN_NOTIONAL set, and requirement is not met, returns False
        """
        limits = self.limits.get(order.symbol)
        if not limits:
            log.fine(f"Limits for {order.symbol} not found")
            return True, None
        min_notional = limits.get(ExchangeLimitationName.MIN_NOTIONAL)
        if not min_notional:
            return True, None

        quantity_in_base_coin = order.quantity * order.price

        return quantity_in_base_coin >= min_notional, f"{order.quantity} {order.symbol} ({quantity_in_base_coin} in " \
                                                      f"base coin) < {min_notional}"

    def _build_exchange_limitations(self, binance_exchange_info: Dict):
        for s in binance_exchange_info.get('symbols'):
            market = s.get("symbol")
            market_dict = dict()
            filters = s.get("filters")
            for f in filters:
                if f.get("filterType") == "PRICE_FILTER":
                    market_dict[ExchangeLimitationName.MIN_PRICE_STEP] = self._get_value(f, "tickSize")
                elif f.get("filterType") == "LOT_SIZE":
                    market_dict[ExchangeLimitationName.MIN_VOLUME_STEP] = self._get_value(f, "stepSize")
                elif f.get("filterType") == "MIN_NOTIONAL":
                    # Min notional is set in base coin (e.g. BTCBUSD: 10 => 10 BUSD)
                    market_dict[ExchangeLimitationName.MIN_NOTIONAL] = self._get_value(f, "minNotional")
            self.limits[market] = market_dict

    def _get_value(self, f: Dict, key: str):
        return float(self._remote_trailing_zeros(f.get(key)))

    @staticmethod
    def _remote_trailing_zeros(str_float: Union[str, float]) -> str:
        return str(float(str_float))
