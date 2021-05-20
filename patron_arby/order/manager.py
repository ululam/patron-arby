import logging
import threading
from decimal import Decimal
from typing import Dict, List

from patron_arby.common.bus import Bus
from patron_arby.common.chain import AChain, AChainStep
from patron_arby.common.decorators import safely
from patron_arby.common.exchange_limitation import ExchangeLimitation
from patron_arby.common.order import Order
from patron_arby.common.util import to_decimal
from patron_arby.config.base import ORDER_PROFIT_THRESHOLD_USD
from patron_arby.db.arbitrage_dao import ArbitrageDao

log = logging.getLogger(__name__)


SENTINEL_MESSAGE = "SHUTDOWN"


class OrderManager(threading.Thread):
    def __init__(self, bus: Bus, exchange_limitations: Dict[str, Dict[ExchangeLimitation, object]],
                 arbitrage_dao: ArbitrageDao) -> None:
        """
        :param bus: Message bus
        :param exchange_limitations: Dictionary of exchange limitations for all trading pairs
        """
        super().__init__()
        self.bus = bus
        self.exchange_limitations = exchange_limitations
        self.arbitrage_dao = arbitrage_dao

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

        self._on_arbitrage_option_found(msg)

    def _on_arbitrage_option_found(self, chain: AChain):
        log.debug(f"Processing {chain.to_user_readable()}")

        if not self._should_process(chain):
            return

        orders = self._create_orders(chain)

        # First, register in running orders
        self.bus.running_orders_storage[chain.to_chain()] = set([o.client_order_id for o in orders])
        # Then, fire!
        for o in orders:
            self.bus.fire_orders_queue.put(o)

        for o in orders:
            log.debug(f"Put order {o}")

        # Save arbitrage
        # todo Move to a dedicated listener & pub/sub
        self.arbitrage_dao.put_profitable_arbitrage(chain)

    def _should_process(self, chain: AChain):
        # todo Calc risk/profit as threshold https://linear.app/good-it-works/issue/ACT-413
        if chain.profit_usd < ORDER_PROFIT_THRESHOLD_USD:
            log.info(f"Chain profit ${chain.profit_usd} is less than threshold ${ORDER_PROFIT_THRESHOLD_USD}, skipping")
            return False

        chain_running_order_ids = self.bus.running_orders_storage.get(chain.to_chain())
        if chain_running_order_ids and len(chain_running_order_ids) > 0:
            log.warning(f"Chain {chain.to_chain()} {len(chain_running_order_ids)} orders are still in progress, "
                        f"skipping")
            return False

        return True

    def _create_orders(self, chain: AChain) -> List[Order]:
        index = 0
        order_list = list()
        for step in chain.steps:
            index += 1
            client_order_id = f"{OrderManager._hash8(chain)}_order_{index}"
            price = OrderManager._calc_break_even_price(step, chain)
            symbol = step.market.replace("/", "")
            order = Order(client_order_id=client_order_id, order_side=step.side, symbol=symbol,
                quantity=step.volume, price=price)
            order.arbitrage_id = chain.uid()

            order = self._align_price_and_volume_to_market_requirements(order)

            order_list.append(order)

        return order_list

    @staticmethod
    def _hash8(chain: AChain):
        return abs(hash(chain.to_chain())) % (10 ** 8)

    # todo https://linear.app/good-it-works/issue/ACT-417
    # todo Shouldn't API do that?
    def _align_price_and_volume_to_market_requirements(self, order: Order):
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
