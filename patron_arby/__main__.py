import logging
import threading
import time
from queue import Queue
from typing import Dict, List

from patron_arby.arbitrage.arby import PetroniusArbiter
from patron_arby.arbitrage.market_data import MarketData
from patron_arby.common.decorators import log_execution_time, safely
from patron_arby.db.arbitrage_dao import ArbitrageDao
from patron_arby.exchange.binance.api import BinanceApi
from patron_arby.exchange.binance.listener import BinanceDataListener

log = logging.getLogger("patron_arby.main")


def run_arbitrage():
    # Wait some time for data to come
    time.sleep(5)

    while True:
        time.sleep(0.1)
        result = petronius_arbiter.find()
        if len(result) == 0:
            continue

        save_top_arbitrage(result)

        positive_result = [r for r in result if float(r.get("roi")) > 0]
        if len(positive_result) == 0:
            log.info(f"PETRONIUS ARBITER found no profit. Best ROI is {result[0]}")
            continue
        else:
            log.info("Found $$$$$$$$")
            save_profitable_arbitrage(positive_result)
            for pr in positive_result:
                print(pr)


@safely
@log_execution_time
def save_profitable_arbitrage(positive_result: List[Dict]):
    for pr in positive_result:
        dao.put_profitable_arbitrage(pr)


def save_top_arbitrage(records: List[Dict]):
    records.sort(key=lambda val: -float(val.get("roi")))
    arbitrage_record_queue.put(records[:10])


def write_data():
    while True:
        time.sleep(0.1)
        while not arbitrage_record_queue.empty():
            dao.put_arbitrage_records(arbitrage_record_queue.get())


arbitrage_record_queue = Queue()

binance_api = BinanceApi()
market_data = MarketData(binance_api.get_symbol_to_base_quote_mapping())
petronius_arbiter = PetroniusArbiter(market_data, binance_api.get_arbitrage_commission())
bl = BinanceDataListener(market_data)
dao = ArbitrageDao()

if __name__ == "__main__":
    listener_thread = threading.Thread(target=bl.run)
    arby_thread = threading.Thread(target=run_arbitrage)
    data_writer_thread = threading.Thread(target=write_data)

    listener_thread.start()
    arby_thread.start()
    data_writer_thread.start()

    listener_thread.join()
    arby_thread.join()
    data_writer_thread.join()
