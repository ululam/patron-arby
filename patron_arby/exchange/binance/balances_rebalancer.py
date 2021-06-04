import logging
from statistics import mean
from typing import Optional, Set

from patron_arby.common.order import Order, OrderSide
from patron_arby.config.base import (
    ARBITRAGE_COINS,
    BALANCE_CHECKER_DEVIATION_FROM_MEAN_TO_REBALANCE,
)
from patron_arby.exchange.binance.limitations import BinanceExchangeLimitations
from patron_arby.exchange.exchange_api import ExchangeApi
from patron_arby.exchange.registry import Balance, BalancesRegistry

log = logging.getLogger(__name__)


class BalancesRebalancer:

    def __init__(self, exchange_api: ExchangeApi,
                 registry: BalancesRegistry,
                 exchange_limitations: BinanceExchangeLimitations,
                 coins_of_interest: Set[str] = ARBITRAGE_COINS,
                 mean_deviation_to_rebalance: float = BALANCE_CHECKER_DEVIATION_FROM_MEAN_TO_REBALANCE) -> None:
        super().__init__()
        self.exchange_api = exchange_api
        self.registry = registry
        self.exchange_limitations = exchange_limitations
        self.coins_of_interest = coins_of_interest
        self.mean_deviation_to_rebalance = mean_deviation_to_rebalance
        log.info(f"Rebalance will happen when max coin balance difference makes {mean_deviation_to_rebalance} out of "
                 f"mean balances value")

    def check_and_fix_disbalance(self):
        balances = self.registry.get_balances(self.coins_of_interest)
        # Remove Nones
        balances = {coin: Balance(bal.value if bal else 0, bal.value_usd if bal.value_usd else 0)
                    for coin, bal in balances.items()}
        coin_max, value_max = max(balances.items(), key=lambda x: x[1].value_usd)
        coin_min, value_min = min(balances.items(), key=lambda x: x[1].value_usd)
        value_usd_avg = mean([v.value_usd for v in balances.values()])
        if (value_max.value_usd - value_min.value_usd) / value_usd_avg > self.mean_deviation_to_rebalance:
            log.info(f"Got big difference in balances, going to rebalance: {coin_min} => {value_min} << "
                     f"{coin_max} => {value_max}. Avg is {value_usd_avg}")

            self._rebalance(coin_max, coin_min, (value_usd_avg - value_min.value_usd))

    def _rebalance(self, donor_coin: str, recipient_coin: str, value_usd: float):
        # todo Fix USD rate
        order = self._rebalance_buy(donor_coin, recipient_coin, value_usd)
        if not order:
            order = self._rebalance_sell(donor_coin, recipient_coin, value_usd)
            if not order:
                log.warning(f"There is no direct market between {donor_coin} and {recipient_coin}")
                return

        order = self.exchange_limitations.adjust_price_and_volume_to_market_requirements(order)
        log.debug(f"Putting market order {order}")
        self.exchange_api.put_market_order(order)

    def _rebalance_buy(self, donor_coin: str, recipient_coin: str, value_usd: float) -> Optional[Order]:
        market_buy = f"{recipient_coin}{donor_coin}"
        exchange_rate = self.registry.get_exchange_rate(market_buy)
        if not exchange_rate:
            return None

        return Order(None, OrderSide.BUY, market_buy, quantity=value_usd / exchange_rate, price=0)

    def _rebalance_sell(self, donor_coin: str, recipient_coin: str, value_usd: float) -> Optional[Order]:
        market_sell = f"{donor_coin}{recipient_coin}"
        exchange_rate = self.registry.get_exchange_rate(market_sell)
        if not exchange_rate:
            return None
        return Order(None, OrderSide.SELL, market_sell, quantity=value_usd / exchange_rate, price=0)
