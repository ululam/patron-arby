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
from patron_arby.order.recent_arbitragers_filter import RecentArbitragersFilter

log = logging.getLogger(__name__)


SENTINEL_MESSAGE = "SHUTDOWN"


class OrderManager(threading.Thread):
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

        comment = self._on_arbitrage_option_found(msg)
        # Here, we have chain with comment. Pass it downstream for saving
        msg.comment = comment
        self.bus.store_positive_arbitrages_queue.put(msg)

    @safely
    def _on_arbitrage_option_found(self, chain: AChain) -> str:
        log.debug(f"Processing {chain.to_user_readable()}")

        if self.recent_arbitragers_filter.register_and_return_contained(chain):
            return "Won't process as considering as duplication (then same arbitrage within a short time frame)"

        if not self._check_profit_is_large_enough(chain):
            return "Arbitrage profit is too low"

        balances = self.balances_registry.get_balances(self.exchange_name)
        chain = self._shrink_volumes_according_to_balances(chain, balances)

        orders, message = self._create_orders(chain)
        if orders and len(orders) > 0:
            for o in orders:
                self.bus.fire_orders_queue.put(o)
                log.debug(f"Put order {o}")

        return message

    @staticmethod
    def _check_profit_is_large_enough(chain: AChain):
        # todo Calc risk/profit as threshold https://linear.app/good-it-works/issue/ACT-413
        if chain.profit_usd < ORDER_PROFIT_THRESHOLD_USD:
            log.info(f"Chain profit ${chain.profit_usd} is less than threshold ${ORDER_PROFIT_THRESHOLD_USD}, skipping")
            return False

        return True

    def _shrink_volumes_according_to_balances(self, chain: AChain, balances: Dict[str, float],
            max_balance_ratio_per_order: float = MAX_BALANCE_RATIO_PER_SINGLE_ORDER) -> AChain:
        if not balances or len(balances) == 0:
            log.debug(f"Not balances found for {self.exchange_name}")
            return chain
        max_step_volume_to_balance_ratio = 0
        for step in chain.steps:
            step_selling_coin_balance = balances.get(step.spending_coin())
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

    def _create_orders(self, chain: AChain) -> Tuple[List[Order], str]:
        index = 0
        order_list = list()
        for step in chain.steps:
            index += 1
            client_order_id = f"{chain.hash8()}_order_{index}"
            price = OrderManager._calc_break_even_price(step, chain)
            symbol = step.market.replace("/", "")
            order = Order(client_order_id=client_order_id, order_side=step.side, symbol=symbol,
                quantity=step.volume, price=price, arbitrage_hash8=chain.hash8())

            order = self._round_price_and_volume_to_market_requirements(order)

            meets_notional, msg = self._meets_min_notional(order)
            if not meets_notional:
                message = f"Order does not meet MIN_NOTIONAL filter ({msg}), skipping the whole chain: {order}"
                log.warning(message)
                # If min min_notional is not met, put no orders
                return list(), f"Order does not meet MIN_NOTIONAL filter ({msg})"

            order_list.append(order)

        return order_list, "Orders created successfully"

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
