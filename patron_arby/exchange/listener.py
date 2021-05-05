import json
import logging
import math
from typing import Dict, List, Tuple, Union

from unicorn_binance_websocket_api.unicorn_binance_websocket_api_manager import (
    BinanceWebSocketApiManager,
)

from patron_arby.arbitrage.market_data import MarketData
from patron_arby.settings import BINANCE_API_KEY, BINANCE_API_SECRET

log = logging.getLogger(__name__)


class BinanceDataListener:
    """
    Component which opens a websocket connection to Binance and listens to ticker and trade blotter events

    See also https://binance-docs.github.io/apidocs/spot/en/#user-data-streams
    """

    ws_manager: BinanceWebSocketApiManager = None
    channels = ["bookTicker"]

    def __init__(self, market_data: MarketData) -> None:
        super().__init__()
        self.market_data = market_data

    def run(self):
        binance_api_key, binance_api_secret = BINANCE_API_KEY, BINANCE_API_SECRET

        self.ws_manager = BinanceWebSocketApiManager(
            # todo Test/Prod mode
            # exchange="binance.com-testnet"
            exchange="binance.com"
        )

        coins, markets = self._get_all_coins_and_markets(binance_api_key, binance_api_secret)
        log.info(f"Totally markets: {len(markets)}")

        self.market_data.set_coins_and_markets(coins, markets)

        self._create_streams(markets)

        while True:
            oldest_stream_data_from_stream_buffer = (
                self.ws_manager.pop_stream_data_from_stream_buffer()
            )
            if not oldest_stream_data_from_stream_buffer:
                continue

            ticker_event = self._filter_events(oldest_stream_data_from_stream_buffer)
            if not ticker_event:
                continue

            self.market_data.put(ticker_event)

    def _get_all_coins_and_markets(self, binance_api_key: str, binance_api_secret: str) -> Tuple[List[str], List[str]]:
        # binance_rest_client = Client(binance_api_key, binance_api_secret)
        # coins = [item['coin'] for item in binance_rest_client.get_all_coins_info()]
        # markets = [item['symbol'] for item in binance_rest_client.get_all_tickers()]
        # return coins, markets
        return ["BTC", "USDT", "ETH"], ["BTCUSDT", "ETHBTC", "ETHUSDT"]

    def _create_streams(self, markets: List):
        divisor = math.ceil(len(markets) / self.ws_manager.get_limit_of_subscriptions_per_stream())
        max_subscriptions = math.ceil(len(markets) / divisor)

        for channel in self.channels:
            if len(markets) <= max_subscriptions:
                self.ws_manager.create_stream(channel, markets, stream_label=channel)
                continue
            loops = 1
            i = 1
            markets_sub = []
            for market in markets:
                markets_sub.append(market)
                if i == max_subscriptions or loops * max_subscriptions + i == len(markets):
                    self.ws_manager.create_stream(channel, markets_sub, stream_label=str(channel + "_" + str(i)),
                        ping_interval=10, ping_timeout=10, close_timeout=5)
                    markets_sub = []
                    i = 1
                    loops += 1
                i += 1

    @staticmethod
    def _filter_events(stream_event) -> Union[Dict, None]:
        try:
            event = json.loads(stream_event)
            return event
        except Exception as e:
            log.error(f"Error during filtering event {stream_event}", exc_info=e)
        return None
