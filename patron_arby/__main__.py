import logging
import threading
import time
from typing import List, Set

from patron_arby.arbitrage.arbitrage_event_listener import ArbitrageEventListener
from patron_arby.arbitrage.arbitrage_thread import ArbitrageThread
from patron_arby.arbitrage.arby import PetroniusArbiter
from patron_arby.arbitrage.market_data import MarketData
from patron_arby.common.bus import Bus
from patron_arby.common.chain import AChain
from patron_arby.common.decorators import safely
from patron_arby.config.base import (
    ARBITRAGE_COINS,
    ARBITRAGE_FIRE_CHAIN_ASAP,
    BALANCE_CHECKER_PERIOD_SECONDS,
    BALANCE_UPDATER_PERIOD_SECONDS,
    BINANCE_LIMIT_ORDER_DEFAULT_TIME_IN_FORCE,
    KINESIS_MAX_BATCH_SIZE,
    ORDER_EXECUTORS_NUMBER,
    POSITIVE_ARBITRAGE_STORE_PERIOD_SECONDS,
    BinanceTimeInForce,
)
from patron_arby.db.arbitrage_dao import ArbitrageDao
from patron_arby.db.keys_provider import KeysProvider
from patron_arby.db.order_dao import OrderDao
from patron_arby.exchange.binance.api import BinanceApi
from patron_arby.exchange.binance.balances_checker import BalancesChecker
from patron_arby.exchange.binance.balances_rebalancer import BalancesRebalancer
from patron_arby.exchange.binance.limitations import BinanceExchangeLimitations
from patron_arby.exchange.binance.listener import BinanceDataListener
from patron_arby.exchange.binance.order_listener import BinanceOrderListener
from patron_arby.exchange.order_cancelator import OrderCancelator
from patron_arby.exchange.registry import BalancesRegistry
from patron_arby.trade.executor import OrderExecutor
from patron_arby.trade.manager import TradeManager

log = logging.getLogger("patron_arby.main")

bus = Bus()
balances_registry = BalancesRegistry()
balances_checker = BalancesChecker(bus, balances_registry, ARBITRAGE_COINS)


class Main:
    @staticmethod
    def _on_positive_arbitrage_found_callback(chains: Set[AChain]):
        bus.positive_arbitrages_queue.put(chains)
        # Again fired in OrderManager, to have processing comment
        # bus.store_positive_arbitrages_queue.put(chain)

    def _update_balances(self):
        while True:
            time.sleep(BALANCE_UPDATER_PERIOD_SECONDS)
            self._safe_update_balances()
            self._safe_update_exchange_rates()

    def _check_balances(self) -> None:
        while True:
            time.sleep(BALANCE_CHECKER_PERIOD_SECONDS)
            balances_checker.check_balance()
            self._safe_check_and_fix_disbalance()

    @safely
    def _safe_update_balances(self):
        balances_registry.update_balances(self.binance_api.get_balances())

    @safely
    def _safe_update_exchange_rates(self):
        balances_registry.update_exchange_rates(self.binance_api.get_latest_prices())

    @safely
    def _safe_check_and_fix_disbalance(self):
        self.balances_rebalancer.check_and_fix_disbalance()

    def _run_store_arbitrages(self):
        # Max size kinesis accepts is 500. Make it twice lower to ensure no overfill happens
        chain_buffer_size = KINESIS_MAX_BATCH_SIZE >> 1
        chains_buffer: List[AChain] = list()
        while True:
            # todo Queue is growing FASTER than we can process it, even with the buffer
            chains = bus.all_arbitrages_queue.get()
            chains_buffer += chains
            if len(chains_buffer) >= chain_buffer_size:
                self.arbitrage_dao.put_arbitrage_records(chains_buffer)
                chains_buffer.clear()

    def _run_store_positive_arbitrage(self):
        while True:
            time.sleep(POSITIVE_ARBITRAGE_STORE_PERIOD_SECONDS)
            chain = bus.store_positive_arbitrages_queue.get()
            self.arbitrage_dao.put_profitable_arbitrage(chain)

    def main(self, keys_provider: KeysProvider = KeysProvider()):
        # Create components
        self.keys_provider = keys_provider
        self.binance_api = BinanceApi(keys_provider)
        self.arbitrage_dao = ArbitrageDao()
        self.balances_rebalancer = BalancesRebalancer(self.binance_api, balances_registry,
            BinanceExchangeLimitations(self.binance_api.get_exchange_info()),
            balances_checker.coins_of_interest)

        market_data = self._create_market_data()

        petronius_arbiter = self._create_arby(market_data)

        order_manager = self._create_order_manager(bus, balances_registry)

        order_dao = OrderDao()
        order_executors = self._create_order_executors(order_dao, market_data, balances_checker)

        exchange_data_listener = BinanceDataListener(market_data, keys_provider,
            set(self.binance_api.get_all_markets()))

        exchange_data_listener.add_event_listener(BinanceOrderListener(bus, order_dao))     # todo Via Bus?
        exchange_data_listener.add_event_listener(ArbitrageEventListener(bus))

        listener_thread = threading.Thread(target=exchange_data_listener.run)
        arby_thread = ArbitrageThread(bus, petronius_arbiter)
        balance_updater_thread = threading.Thread(target=self._update_balances)
        balance_checker_thread = threading.Thread(target=self._check_balances)
        arbitrages_store_thread = threading.Thread(target=self._run_store_arbitrages)
        positive_arbitrages_store_thread = threading.Thread(target=self._run_store_positive_arbitrage)

        # Run everything
        balance_updater_thread.start()
        balance_checker_thread.start()
        listener_thread.start()
        arby_thread.start()
        order_manager.start()
        arbitrages_store_thread.start()
        positive_arbitrages_store_thread.start()
        for order_exec in order_executors:
            order_exec.start()

        self._run_order_cancelator_if_needed(self.binance_api, market_data)

        listener_thread.join()

    def _create_market_data(self) -> MarketData:
        return MarketData(self.binance_api.get_symbol_to_base_quote_mapping(), only_coins=ARBITRAGE_COINS)

    def _create_arby(self, market_data: MarketData) -> PetroniusArbiter:
        return PetroniusArbiter(
            market_data,
            self.binance_api.get_trade_fees(),
            self._on_positive_arbitrage_found_callback,
            ARBITRAGE_FIRE_CHAIN_ASAP,
            self.binance_api.get_default_trade_fee()
        )

    def _run_order_cancelator_if_needed(self, binance_api: BinanceApi, market_data: MarketData):
        if BINANCE_LIMIT_ORDER_DEFAULT_TIME_IN_FORCE == BinanceTimeInForce.GOOD_TILL_CANCELLED:
            order_cancelator = OrderCancelator(binance_api, market_data)
            order_cancelator.start()

    def _create_order_manager(self, a_bus: Bus, registry: BalancesRegistry):
        limitations = BinanceExchangeLimitations(self.binance_api.get_exchange_info())
        return TradeManager(a_bus, limitations, registry)

    def _create_order_executors(self, order_dao: OrderDao, market_data: MarketData, balances_checker: BalancesChecker) \
            -> List[OrderExecutor]:
        order_executors: List[OrderExecutor] = list()
        for i in range(0, ORDER_EXECUTORS_NUMBER):
            order_executors.append(
                OrderExecutor(bus, BinanceApi(self.keys_provider), order_dao, market_data, balances_checker))
        return order_executors


if __name__ == "__main__":
    Main().main()
