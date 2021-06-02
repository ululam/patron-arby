import logging
from decimal import Decimal
from typing import Dict, Optional, Union

from patron_arby.config.base import DEFAULT_USD_COIN

log = logging.getLogger(__name__)


class BalancesRegistry:

    def __init__(self, balances: Dict[str, float] = None, exchange_rates: Dict[str, float] = None,
                 usd_coin: str = DEFAULT_USD_COIN) -> None:
        self.balances = balances if balances else dict()
        self.exchange_rates = exchange_rates if exchange_rates else dict()
        self.usd_coin = usd_coin

    def get_balance(self, coin: str) -> Optional[float]:
        return self.balances.get(coin)

    def get_balance_usd(self, coin: str) -> Optional[float]:
        if self.is_empty():
            return None
        balance = self.get_balance(coin)
        if not balance:
            log.warning(f"No balance found for {coin}")
            return None
        if self._is_usd_coin(coin):
            # Let's neglect USD coins cross echange rates (e.g. we consider BUSD = USDT, for the purpose of balance)
            return balance

        if not self.exchange_rates or len(self.exchange_rates) == 0:
            return None
        # We suggest that we always have trading pair coin/usd_coin
        market = f"{coin}{self.usd_coin}"
        exchange_rate = self.exchange_rates.get(market)
        if not exchange_rate:
            log.warning(f"No exchange rate found for {coin}")
            return None

        return balance * exchange_rate

    def update_balances(self, balances: Dict[str, float]):
        self.balances = balances

    def reduce_balance(self, coin: str, volume: Union[float, Decimal]):
        """
        Substracts given volume from the given coin balance.
        Its expected and by design that the next `update_balances` call will erase any reductions happenned
        (https://linear.app/good-it-works/issue/ACT-440)
        :param coin:
        :param volume:
        :return:
        """
        amount = self.balances.get(coin)
        # Can potentially go below 0, but there's no harm in it. Yet issue a warning
        new_amount = amount - float(volume)
        if new_amount < 0:
            log.warning(f"{coin} balance went below zero. Was {amount}, became {new_amount}")
        self.balances[coin] = new_amount

    def update_exchange_rates(self, exchange_rates: Dict):
        self.exchange_rates = exchange_rates

    def is_empty(self):
        return not self.balances or len(self.balances) == 0

    def _is_usd_coin(self, coin: str):
        return "USD" in coin
