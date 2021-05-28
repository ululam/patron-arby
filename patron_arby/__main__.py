import logging
import threading
import time
from typing import List

from patron_arby.arbitrage.arbitrage_event_listener import ArbitrageEventListener
from patron_arby.arbitrage.arbitrage_thread import ArbitrageThread
from patron_arby.arbitrage.arby import PetroniusArbiter
from patron_arby.arbitrage.market_data import MarketData
from patron_arby.common.bus import Bus
from patron_arby.common.chain import AChain
from patron_arby.common.decorators import safely
from patron_arby.config.base import (
    ARBITRAGE_COINS,
    BALANCE_CHECKER_PERIOD_SECONDS,
    KINESIS_MAX_BATCH_SIZE,
    POSITIVE_ARBITRAGE_STORE_PERIOD_SECONDS,
)
from patron_arby.db.arbitrage_dao import ArbitrageDao
from patron_arby.db.keys_provider import KeysProvider
from patron_arby.db.order_dao import OrderDao
from patron_arby.exchange.binance.api import BinanceApi
from patron_arby.exchange.binance.constants import Binance
from patron_arby.exchange.binance.limitations import BinanceExchangeLimitations
from patron_arby.exchange.binance.listener import BinanceDataListener
from patron_arby.exchange.binance.order_listener import BinanceOrderListener
from patron_arby.exchange.registry import BalancesRegistry
from patron_arby.trade.executor import OrderExecutor
from patron_arby.trade.manager import TradeManager

log = logging.getLogger("patron_arby.main")

bus = Bus()
balances_registry = BalancesRegistry()


class Main:
    @staticmethod
    def _on_positive_arbitrage_found_callback(chain: AChain):
        bus.positive_arbitrages_queue.put(chain)
        # Again fired in OrderManager, to have processing comment
        # bus.store_positive_arbitrages_queue.put(chain)

    def _update_balances(self):
        while True:
            time.sleep(BALANCE_CHECKER_PERIOD_SECONDS)
            self._safe_update_balances()

    @safely
    def _safe_update_balances(self):
        balances_registry.set_balances(Binance.NAME, self.binance_api.get_balances())

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
        self.binance_api = BinanceApi(keys_provider)
        self.arbitrage_dao = ArbitrageDao()

        market_data = self._create_market_data()

        petronius_arbiter = self._create_arby(market_data)

        order_manager = self._create_order_manager(bus, balances_registry)

        order_dao = OrderDao()
        order_executors = self._create_order_executors(order_dao)

        exchange_data_listener = BinanceDataListener(market_data, keys_provider,
            set(self.binance_api.get_all_markets()))
        exchange_data_listener.add_event_listener(BinanceOrderListener(bus, order_dao))     # todo Via Bus?
        exchange_data_listener.add_event_listener(ArbitrageEventListener(bus))

        listener_thread = threading.Thread(target=exchange_data_listener.run)
        arby_thread = ArbitrageThread(bus, petronius_arbiter)
        balance_updater = threading.Thread(target=self._update_balances)
        arbitrages_store_thread = threading.Thread(target=self._run_store_arbitrages)
        positive_arbitrages_store_thread = threading.Thread(target=self._run_store_positive_arbitrage)

        # Run everything
        balance_updater.start()
        listener_thread.start()
        arby_thread.start()
        order_manager.start()
        arbitrages_store_thread.start()
        positive_arbitrages_store_thread.start()
        for order_exec in order_executors:
            order_exec.start()

        listener_thread.join()

    def _create_market_data(self) -> MarketData:
        return MarketData(self.binance_api.get_symbol_to_base_quote_mapping(), only_coins=ARBITRAGE_COINS)

    def _create_arby(self, market_data: MarketData) -> PetroniusArbiter:
        return PetroniusArbiter(
            market_data,
            self.binance_api.get_trade_fees(),
            self._on_positive_arbitrage_found_callback,
            self.binance_api.get_default_trade_fee()
        )

    def _create_order_manager(self, a_bus: Bus, registry: BalancesRegistry):
        limitations = BinanceExchangeLimitations(self.binance_api.get_exchange_info())
        return TradeManager(a_bus, limitations.get_limitations(), registry)

    def _create_order_executors(self, order_dao: OrderDao) -> List[OrderExecutor]:
        order_executors: List[OrderExecutor] = list()
        for i in range(0, 1):
            order_executors.append(
                OrderExecutor(bus, self.binance_api, order_dao))
        return order_executors


if __name__ == "__main__":
    Main().main()
