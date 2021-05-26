import logging
import threading
import time
from typing import Dict, List, Union

from patron_arby.arbitrage.arbitrage_event_listener import ArbitrageEventListener
from patron_arby.arbitrage.arby import PetroniusArbiter
from patron_arby.arbitrage.market_data import MarketData
from patron_arby.common.bus import Bus
from patron_arby.common.chain import AChain
from patron_arby.common.decorators import safely
from patron_arby.common.exchange_limitation import ExchangeLimitation
from patron_arby.config.base import ARBITRAGE_COINS
from patron_arby.db.arbitrage_dao import ArbitrageDao
from patron_arby.db.keys_provider import KeysProvider
from patron_arby.db.order_dao import OrderDao
from patron_arby.exchange.binance.api import BinanceApi
from patron_arby.exchange.binance.constants import Binance
from patron_arby.exchange.binance.listener import BinanceDataListener
from patron_arby.exchange.binance.order_listener import BinanceOrderListener
from patron_arby.exchange.registry import BalancesRegistry
from patron_arby.order.executor import OrderExecutor
from patron_arby.order.manager import OrderManager

log = logging.getLogger("patron_arby.main")

bus = Bus()
balances_registry = BalancesRegistry()


class Main:
    def _run_arbitrage(self):
        # Wait some time for data to come
        time.sleep(3)

        exec_count = 0
        while True:
            ticker = bus.tickers_queue.get()
            self.petronius_arbiter.find({ticker.market})
            exec_count += 1
            if exec_count % 100 == 0:
                log.info(f"Ran arbitrage {exec_count} times")

    @staticmethod
    def _on_positive_arbitrage_found_callback(chain: AChain):
        bus.arbitrage_findings_queue.put(chain)

    def _build_exchange_limitations(self, binance_exchange_info: Dict) -> Dict:
        limits = dict()
        for s in binance_exchange_info.get('symbols'):
            market = s.get("symbol")
            limits[market] = dict()
            filters = s.get("filters")
            for f in filters:
                if f.get("filterType") == "PRICE_FILTER":
                    limits[market][ExchangeLimitation.MIN_PRICE_STEP] = self._remote_trailing_zeros(f.get("tickSize"))
                elif f.get("filterType") == "LOT_SIZE":
                    limits[market][ExchangeLimitation.MIN_VOLUME_STEP] = self._remote_trailing_zeros(f.get("stepSize"))

        return limits

    @staticmethod
    def _remote_trailing_zeros(str_float: Union[str, float]) -> str:
        return str(float(str_float))

    def _update_balances(self):
        while True:
            time.sleep(1)
            self._safe_update_balances()

    @safely
    def _safe_update_balances(self):
        balances_registry.set_balances(Binance.NAME, self.binance_api.get_balances())

    def main(self, keys_provider: KeysProvider = KeysProvider()):
        # Create components
        self.binance_api = BinanceApi(keys_provider)

        market_data = self._create_market_data()

        self.petronius_arbiter = self._create_arby(market_data)

        order_manager = self._create_order_manager(bus, ArbitrageDao(), balances_registry)

        order_dao = OrderDao()

        order_executors = self._create_order_executors(order_dao)

        exchange_data_listener = BinanceDataListener(market_data, keys_provider,
            set(self.binance_api.get_all_markets()))
        exchange_data_listener.add_event_listener(BinanceOrderListener(bus, order_dao))     # todo Via Bus?
        exchange_data_listener.add_event_listener(ArbitrageEventListener(bus))

        listener_thread = threading.Thread(target=exchange_data_listener.run)
        arby_thread = threading.Thread(target=self._run_arbitrage)
        balance_updater = threading.Thread(target=self._update_balances)

        # Run everything
        balance_updater.start()
        listener_thread.start()
        arby_thread.start()
        order_manager.start()
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

    def _create_order_manager(self, a_bus: Bus, arbitrage_dao: ArbitrageDao, registry: BalancesRegistry):
        return OrderManager(
            a_bus,
            self._build_exchange_limitations(self.binance_api.get_exchange_info()),
            arbitrage_dao,
            registry
        )

    def _create_order_executors(self, order_dao: OrderDao) -> List[OrderExecutor]:
        order_executors: List[OrderExecutor] = list()
        for i in range(0, 1):
            order_executors.append(
                OrderExecutor(bus, self.binance_api, order_dao))
        return order_executors


if __name__ == "__main__":
    Main().main()
