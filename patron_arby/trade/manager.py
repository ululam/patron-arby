import logging
import threading
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from patron_arby.common.bus import Bus
from patron_arby.common.chain import AChain, AChainStep
from patron_arby.common.decorators import safely
from patron_arby.common.exchange_limitation import ExchangeLimitation
from patron_arby.common.order import Order
from patron_arby.common.util import to_decimal
from patron_arby.config.base import (
    MAX_BALANCE_RATIO_PER_SINGLE_ORDER,
    ORDER_PROFIT_THRESHOLD_USD,
)
from patron_arby.exchange.binance.constants import Binance
from patron_arby.exchange.registry import BalancesRegistry
from patron_arby.trade.recent_arbitragers_filter import RecentArbitragersFilter

log = logging.getLogger(__name__)


SENTINEL_MESSAGE = "SHUTDOWN"


class TradeManager(threading.Thread):
    # todo Set on creation
    exchange_name = Binance.NAME

    def __init__(self,
                 bus: Bus,
                 exchange_limitations: Dict[str, Dict[ExchangeLimitation, float]],
                 balances_registry: BalancesRegistry) -> None:
        """
        :param bus: Message bus
        :param exchange_limitations: Dictionary of exchange limitations for all trading pairs
        """
        super().__init__()
        self.bus = bus
        self.exchange_limitations = exchange_limitations
        self.balances_registry = balances_registry
        self.recent_arbitragers_filter = RecentArbitragersFilter()

    def run(self) -> None:
        log.debug("Starting")
        while True:
            msg = self.bus.positive_arbitrages_queue.get(block=True)
            if msg == SENTINEL_MESSAGE:
                break
            self._process(msg)
        log.debug("Ending")

    @safely
    def _process(self, msg):
        if not isinstance(msg, AChain):
            log.error(f"Message should be either of type {AChain} or == '{SENTINEL_MESSAGE}' for quit. "
                      f"Got {msg}, skipping")
            return

        if self.bus.is_stop_trading:
            comment = "Stop trading flag is True, ignoring arbitrage chain"
            log.debug(f"{comment}: {msg.uid()}")
        else:
            comment = self._on_arbitrage_option_found(msg)
            log.debug(comment)
        # Here, we have chain with comment. Pass it downstream for saving
        msg.comment = comment
        self.bus.store_positive_arbitrages_queue.put(msg)

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

        orders = [self._round_price_and_volume_to_market_requirements(order) for order in orders]

        meets_all_filters, error = self._check_meets_exchange_filters(orders)
        if not meets_all_filters:
            return error

        self._put_orders_to_execution_queue(orders, chain)

        return "Orders created successfully"

    def _put_orders_to_execution_queue(self, orders: List[Order], chain: AChain):
        for order, step in zip(orders, chain.steps):
            # Put to the queue for order executors to pick up
            self.bus.fire_orders_queue.put(order)
            # Extract order volume from local cache to prevent setting next order(s) when balance is actually consumed
            # by previous order(s) yet not really reflected in the balance itself (order(s) is in fly, waiting for fill,
            # balance cache has not been refreshed yet)
            # https://linear.app/good-it-works/issue/ACT-440/
            # Here, its important to use orders's volume (not chain's), as orders volumes are subject of adjustment
            self.balances_registry.reduce_balance(step.spending_coin(), order.get_what_we_propose_volume())
            log.debug(f"Put order {order}")

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
            log.debug("No balances set")
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
            meets_notional, msg = self._meets_min_notional(order)
            if not meets_notional:
                # If min min_notional is not met, put no orders
                message = f"Order does not meet MIN_NOTIONAL filter ({msg})"
                log.warning(message + f", skipping the whole chain: {order}")
                return False, message
        return True, "Orders meet all filters"

    def _meets_min_notional(self, order: Order) -> Tuple[bool, Optional[str]]:
        """
        :param order:
        :return: True if order volume meets MIN_NOTIONAL exchange requirement, or if no MIN_NOTIONAL set.
        If MIN_NOTIONAL set, and requirement is not met, returns False
        """
        limits = self.exchange_limitations.get(order.symbol)
        if not limits:
            log.fine(f"Limits for {order.symbol} not found")
            return True, None
        min_notional = limits.get(ExchangeLimitation.MIN_NOTIONAL)
        if not min_notional:
            return True, None

        quantity_in_base_coin = order.quantity * order.price

        return quantity_in_base_coin >= min_notional, f"{order.quantity} {order.symbol} ({quantity_in_base_coin} in " \
                                                      f"base coin) < {min_notional}"

    # todo https://linear.app/good-it-works/issue/ACT-417
    # todo Shouldn't API do that?
    def _round_price_and_volume_to_market_requirements(self, order: Order):
        limits = self.exchange_limitations.get(order.symbol)
        if not limits:
            log.fine(f"Limits for {order.symbol} not found")
            return

        min_price_step = limits.get(ExchangeLimitation.MIN_PRICE_STEP)
        if min_price_step:
            order.price = to_decimal(order.price, Decimal(str(min_price_step)))

        min_volume_step = limits.get(ExchangeLimitation.MIN_VOLUME_STEP)
        if min_volume_step:
            order.quantity = to_decimal(order.quantity, Decimal(str(min_volume_step)))

        return order

    @staticmethod
    # todo Consider price and volume limitation: https://linear.app/good-it-works/issue/ACT-412
    def _calc_break_even_price(step: AChainStep, chain: AChain) -> float:
        # https://linear.app/good-it-works/issue/ACT-411
        # Simple heuristic for break even price
        price_factor = chain.roi / len(chain.steps)
        # Increase price if BUY, decrease if SELL
        price = step.price * (1 + price_factor) if step.is_buy() else step.price * (1 - price_factor)
        return price
