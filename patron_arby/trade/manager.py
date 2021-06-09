import logging
import random
import threading
from typing import List, Set, Tuple

from patron_arby.common.bus import Bus
from patron_arby.common.chain import AChain, AChainStep
from patron_arby.common.decorators import safely
from patron_arby.common.order import Order
from patron_arby.config.base import (
    MAX_BALANCE_RATIO_PER_SINGLE_ORDER,
    ORDER_PROFIT_THRESHOLD_USD,
    TRADE_MANAGER_FIRE_ONLY_TOP_ARBITRAGE,
    TRADE_MANAGER_SORT_ARBITRAGE_BY_ROI,
)
from patron_arby.exchange.binance.constants import Binance
from patron_arby.exchange.exchange_limitations import ExchangeLimitations
from patron_arby.exchange.registry import BalancesRegistry
from patron_arby.trade.recent_arbitragers_filter import RecentArbitragersFilter

log = logging.getLogger(__name__)


SENTINEL_MESSAGE = "SHUTDOWN"


class TradeManager(threading.Thread):
    # todo Set on creation
    exchange_name = Binance.NAME

    def __init__(self,
                 bus: Bus,
                 exchange_limitations: ExchangeLimitations,
                 balances_registry: BalancesRegistry,
                 fire_only_top_arbitrage: bool = TRADE_MANAGER_FIRE_ONLY_TOP_ARBITRAGE,
                 sort_arbitrage_by_roi: bool = TRADE_MANAGER_SORT_ARBITRAGE_BY_ROI) -> None:
        """
        :param bus: Message bus
        :param exchange_limitations: Dictionary of exchange limitations for all trading pairs
        """
        super().__init__()
        self.bus = bus
        self.exchange_limitations = exchange_limitations
        self.balances_registry = balances_registry
        self.fire_only_top_arbitrage = fire_only_top_arbitrage
        self.sort_arbitrage_by_roi = sort_arbitrage_by_roi
        self.recent_arbitragers_filter = RecentArbitragersFilter()

    def run(self) -> None:
        log.debug("Starting")
        while True:
            chains = self.bus.positive_arbitrages_queue.get(block=True)
            if chains == SENTINEL_MESSAGE:
                break

            log.debug(f"Got {len(chains)} chains to process")

            self._process_chain_set(chains)

        log.debug("Ending")

    def _process_chain_set(self, chains: Set[AChain]):
        chains_list = self._sort_chains_by_profitability(chains)

        if self.fire_only_top_arbitrage:
            message = f"Processing only the top chain [{chains_list[0].hash8()}] {chains_list[0]} from the batch"
            log.debug(message)
            self._process_chain(chains_list[0])
            for i in range(1, len(chains_list)):
                chains_list[i].comment = message
        else:
            log.debug(f"Processing all {len(chains_list)} arbitrage chains")
            for chain in chains_list:
                self._process_chain(chain)

        for chain in chains_list:
            self.bus.store_positive_arbitrages_queue.put(chain)

    @safely
    def _process_chain(self, chain: AChain) -> AChain:
        if self.bus.is_stop_trading():
            comment = "Stop trading flag is True, ignoring arbitrage chain"
            log.debug(f"{comment}: {chain.uid()}")
        else:
            comment = self._on_arbitrage_option_found(chain)
            log.debug(comment)
        # Here, we have chain with comment. Pass it downstream for saving
        chain.comment = comment
        return chain

    @safely
    def _on_arbitrage_option_found(self, chain: AChain) -> str:
        log.debug(f"Processing {chain.to_user_readable()}")

        if self.recent_arbitragers_filter.register_and_return_contained(chain):
            return "Won't process as considering as duplication (same arbitrage within a short time frame)"

        if not self._check_profit_is_large_enough(chain):
            return "Arbitrage profit is too low"

        all_balances_above_zero, error = self._check_we_have_all_three_balances_above_zero(chain)
        if not all_balances_above_zero:
            return error

        chain = self._shrink_volumes_according_to_balances(chain)

        orders = self._create_orders(chain)

        orders = [self.exchange_limitations.adjust_price_and_volume_to_market_requirements(order) for order in orders]

        meets_all_filters, error = self._check_meets_exchange_filters(orders)
        if not meets_all_filters:
            return error

        self._put_orders_to_execution_queue(orders)

        self._reduce_cached_balances(orders, chain)

        return "Orders created successfully"

    def _put_orders_to_execution_queue(self, orders: List[Order]):
        # Do not change original list
        orders_copy = orders.copy()
        # Iterate in random order to provide better balances distribution
        random.shuffle(orders_copy)

        for order in orders_copy:
            # Put to the queue for order executors to pick up
            self.bus.fire_orders_queue.put(order)
            log.debug(f"Put order {order}")

    def _reduce_cached_balances(self, orders: List[Order], chain: AChain):
        for order, step in zip(orders, chain.steps):
            # Extract order volume from local cache to prevent setting next order(s) when balance is actually consumed
            # by previous order(s) yet not really reflected in the balance itself (order(s) is in fly, waiting for fill,
            # balance cache has not been refreshed yet)
            # https://linear.app/good-it-works/issue/ACT-440/
            # Here, its important to use orders volume (not chain), as orders volumes are subject of adjustment
            self.balances_registry.reduce_balance(step.spending_coin(), order.get_what_we_propose_volume())

    def _sort_chains_by_profitability(self, chains: Set[AChain]) -> List[AChain]:
        if self.sort_arbitrage_by_roi:
            return sorted(list(chains), key=lambda c: c.roi, reverse=True)
        return sorted(list(chains), key=lambda c: c.profit, reverse=True)

    @staticmethod
    def _check_profit_is_large_enough(chain: AChain):
        # todo Calc risk/profit as threshold https://linear.app/good-it-works/issue/ACT-413
        if chain.profit_usd < ORDER_PROFIT_THRESHOLD_USD:
            log.info(f"Chain profit ${chain.profit_usd} is less than threshold ${ORDER_PROFIT_THRESHOLD_USD}, skipping")
            return False

        return True

    def _check_we_have_all_three_balances_above_zero(self, chain: AChain) -> Tuple[bool, str]:
        for step in chain.steps:
            coin_balance = self.balances_registry.get_balance(step.spending_coin())
            if coin_balance <= 0:
                return False, f"{step.spending_coin()} balance is 0 or below: {coin_balance}"
        return True, "All balances are fine"

    def _shrink_volumes_according_to_balances(self, chain: AChain,
            max_balance_ratio_per_order: float = MAX_BALANCE_RATIO_PER_SINGLE_ORDER) -> AChain:
        if self.balances_registry.is_empty():
            log.warning("No balances set (yet?)")
            return chain
        max_step_volume_to_balance_ratio = 0
        for step in chain.steps:
            step_selling_coin_balance = self.balances_registry.get_balance(step.spending_coin())
            if not step_selling_coin_balance:
                # We have no information about that balance. Hope for the better.
                continue
            step_volume_to_balance_ratio = step.get_what_we_propose_volume() / step_selling_coin_balance

            if step_volume_to_balance_ratio > max_balance_ratio_per_order:
                max_step_volume_to_balance_ratio = max(max_step_volume_to_balance_ratio, step_volume_to_balance_ratio)

        if max_step_volume_to_balance_ratio > 0:
            orders_volume_shrink_factor = max_step_volume_to_balance_ratio / max_balance_ratio_per_order
            log.warning(f"Cutting orders volumes by factor {orders_volume_shrink_factor} because of insufficient "
                        f"balance")
            # Divide all the volumes by the max ratio
            for step in chain.steps:
                step.volume /= orders_volume_shrink_factor

        return chain

    @staticmethod
    def _create_orders(chain: AChain) -> List[Order]:
        index = 0
        order_list = list()
        for step in chain.steps:
            index += 1
            client_order_id = f"{chain.hash8()}_order_{index}"
            price = TradeManager._calc_break_even_price(step, chain)
            symbol = step.market.replace("/", "")
            order = Order(client_order_id=client_order_id, order_side=step.side, symbol=symbol,
                quantity=step.volume, price=price, arbitrage_hash8=chain.hash8())

            order_list.append(order)

        return order_list

    def _check_meets_exchange_filters(self, orders: List[Order]) -> Tuple[bool, str]:
        for order in orders:
            meets_notional, message = self.exchange_limitations.check_meets_exchange_filters(order)
            if not meets_notional:
                log.warning(message + f", skipping the whole chain: {order}")
                return False, message
        return True, "Orders meet all filters"

    @staticmethod
    # todo Consider price and volume limitation: https://linear.app/good-it-works/issue/ACT-412
    def _calc_break_even_price(step: AChainStep, chain: AChain) -> float:
        # https://linear.app/good-it-works/issue/ACT-411
        # Simple heuristic for break even price
        # price_factor = chain.roi / len(chain.steps)
        price_factor = chain.roi
        # Increase price if BUY, decrease if SELL
        price = step.price * (1 + price_factor) if step.is_buy() else step.price * (1 - price_factor)
        return price
