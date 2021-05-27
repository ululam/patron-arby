import logging
import threading
from decimal import Decimal
from typing import Dict, List, Optional

from patron_arby.common.bus import Bus
from patron_arby.common.chain import AChain, AChainStep
from patron_arby.common.decorators import safely
from patron_arby.common.exchange_limitation import ExchangeLimitation
from patron_arby.common.order import Order
from patron_arby.common.util import current_time_ms, to_decimal
from patron_arby.config.base import (
    MAX_BALANCE_RATIO_PER_SINGLE_ORDER,
    ORDER_PROFIT_THRESHOLD_USD,
)
from patron_arby.db.arbitrage_dao import ArbitrageDao
from patron_arby.exchange.binance.constants import Binance
from patron_arby.exchange.registry import BalancesRegistry

log = logging.getLogger(__name__)


SENTINEL_MESSAGE = "SHUTDOWN"


def log_execution_time(args):
    pass


class OrderManager(threading.Thread):
    # todo Set on creation
    exchange_name = Binance.NAME

    def __init__(self,
                 bus: Bus,
                 exchange_limitations: Dict[str, Dict[ExchangeLimitation, object]],
                 arbitrage_dao: ArbitrageDao,
                 balances_registry: BalancesRegistry) -> None:
        """
        :param bus: Message bus
        :param exchange_limitations: Dictionary of exchange limitations for all trading pairs
        """
        super().__init__()
        self.bus = bus
        self.exchange_limitations = exchange_limitations
        self.arbitrage_dao = arbitrage_dao
        self.balances_registry = balances_registry

    def run(self) -> None:
        log.debug("Starting")
        while True:
            msg = self.bus.arbitrage_findings_queue.get(block=True)
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

        return self._on_arbitrage_option_found(msg)

    def _on_arbitrage_option_found(self, chain: AChain):
        log.debug(f"Processing {chain.to_user_readable()}")

        start = current_time_ms()
        orders = self._do_quick_part(chain)
        if not orders:
            # Should not process
            return
        log.debug(f"_do_quick_part() took {(current_time_ms() - start)} ms")

        # Now, we can do some slow activities
        for o in orders:
            log.debug(f"Put order {o}")

        # Save arbitrage
        # todo Move to a dedicated listener & pub/sub
        return self.arbitrage_dao.put_profitable_arbitrage(chain)

    def _do_quick_part(self, chain: AChain) -> Optional[List[Order]]:
        """
        Rather artificial than logical split: this method contain logic that should be done as quick as possible
        """
        if not self._should_process(chain):
            return None

        balances = self.balances_registry.get_balances(self.exchange_name)
        chain = self._shrink_volumes_according_to_balances(chain, balances)

        orders = self._create_orders(chain)

        for o in orders:
            self.bus.fire_orders_queue.put(o)

        return orders

    def _should_process(self, chain: AChain):
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

    def _create_orders(self, chain: AChain) -> List[Order]:
        index = 0
        order_list = list()
        for step in chain.steps:
            index += 1
            client_order_id = f"{chain.hash8()}_order_{index}"
            price = OrderManager._calc_break_even_price(step, chain)
            symbol = step.market.replace("/", "")
            order = Order(client_order_id=client_order_id, order_side=step.side, symbol=symbol,
                quantity=step.volume, price=price)
            order.arbitrage_id = chain.uid()

            order = self._round_price_and_volume_to_market_requirements(order)

            order_list.append(order)

        return order_list

    # todo https://linear.app/good-it-works/issue/ACT-417
    # todo Shouldn't API do that?
    def _round_price_and_volume_to_market_requirements(self, order: Order):
        limits = self.exchange_limitations.get(order.symbol)
        if not limits:
            log.fine(f"Limits for {order.symbol} not found")
            return
        min_price_step = limits.get(ExchangeLimitation.MIN_PRICE_STEP)
        order.price = to_decimal(order.price, Decimal(str(min_price_step)))
        min_volume_step = limits.get(ExchangeLimitation.MIN_VOLUME_STEP)
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
