import logging
import threading
import time
from typing import Dict, List, Union

from patron_arby.arbitrage.arby import PetroniusArbiter
from patron_arby.arbitrage.market_data import MarketData
from patron_arby.common.bus import Bus
from patron_arby.common.chain import AChain
from patron_arby.common.decorators import measure_execution_time, safely
from patron_arby.common.exchange_limitation import ExchangeLimitation
from patron_arby.config.base import ARBITRAGE_COINS
from patron_arby.config.staging import PAPER_API_KEY, PAPER_API_SECRET, PAPER_API_URL
from patron_arby.db.arbitrage_dao import ArbitrageDao
from patron_arby.db.order_dao import OrderDao
from patron_arby.exchange.binance.api import BinanceApi
from patron_arby.exchange.binance.listener import BinanceDataListener
from patron_arby.exchange.binance.order_listener import BinanceOrderListener
from patron_arby.order.executor import OrderExecutor
from patron_arby.order.manager import OrderManager

log = logging.getLogger("patron_arby.main")

bus = Bus()


class Main:
    def run_arbitrage(self):
        # Wait some time for data to come
        time.sleep(3)

        exec_count = 0
        while True:
            # time.sleep(0.1)
            time.sleep(0.1)
            result = self.petronius_arbiter.find(self.on_positive_arbitrage_found_callback)
            exec_count += 1
            if exec_count % 100 == 0:
                log.info(f"Ran arbitrage {exec_count} times")
            if len(result) == 0:
                continue

            self.save_top_arbitrage(result)
            #
            # positive_result = [r for r in result if float(r.get("roi")) > 0]
            # if len(positive_result) == 0:
            #     log.info(f"PETRONIUS ARBITER found no profit. Best ROI is {result[0]}")
            #     continue
            # else:
            #     log.info("Found $$$$$$$$")
            #     save_profitable_arbitrage(positive_result)
            #     for pr in positive_result:
            #         print(pr)

    @staticmethod
    def on_positive_arbitrage_found_callback(chain: AChain):
        bus.arbitrage_findings_queue.put(chain)

    @safely
    @measure_execution_time
    def save_profitable_arbitrage(self, positive_result: List[Dict]):
        for pr in positive_result:
            self.arbitrage_dao.put_profitable_arbitrage(pr)

    def save_top_arbitrage(self, chains: List[AChain]):
        chains.sort(key=lambda val: -val.profit_usd)
        # arbitrage_record_queue.put(chains[:10])
        # for c in chains[:1]:
        #     print(c.to_user_readable())

    def write_data(self):
        pass
        # while True:
        #     time.sleep(0.1)
        #     while not arbitrage_record_queue.empty():
        #         self.dao.put_arbitrage_records(arbitrage_record_queue.get())

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

    def main(self, prod_binance_api: BinanceApi = BinanceApi(),
             put_orders_binance_api: BinanceApi = BinanceApi(PAPER_API_KEY, PAPER_API_SECRET, PAPER_API_URL)):
        market_data = MarketData(prod_binance_api.get_symbol_to_base_quote_mapping(), only_coins=ARBITRAGE_COINS)

        self.petronius_arbiter = PetroniusArbiter(market_data, prod_binance_api.get_trade_fees(),
            prod_binance_api.get_default_trade_fee())

        self.arbitrage_dao = ArbitrageDao()

        order_manager = OrderManager(bus, self._build_exchange_limitations(prod_binance_api.get_exchange_info()),
            self.arbitrage_dao)

        order_dao = OrderDao()

        order_executors: List[OrderExecutor] = list()
        for i in range(0, 1):
            # todo API KEYS
            order_executors.append(
                OrderExecutor(bus, put_orders_binance_api, order_dao))

        orders_listener = BinanceOrderListener(bus, order_dao)

        bl = BinanceDataListener(market_data, prod_binance_api)
        bl.add_event_listener(orders_listener)

        listener_thread = threading.Thread(target=bl.run)
        arby_thread = threading.Thread(target=self.run_arbitrage)
        # data_writer_thread = threading.Thread(target=self.write_data)

        listener_thread.start()
        arby_thread.start()
        order_manager.start()
        for exec in order_executors:
            exec.start()
        # data_writer_thread.start()

        # listener_thread.join()
        # arby_thread.join()
        # order_manager.join()
        # data_writer_thread.join()


if __name__ == "__main__":
    Main().main()
