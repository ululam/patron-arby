import json
import logging
import math
from typing import Dict, List, Union

from unicorn_binance_websocket_api.unicorn_binance_websocket_api_manager import (
    BinanceWebSocketApiManager,
)

from patron_arby.arbitrage.market_data import MarketData
from patron_arby.exchange.binance.api import BinanceApi
from patron_arby.settings import BINANCE_WEB_SOCKET_URL

log = logging.getLogger(__name__)


class BinanceDataListener:
    """
    Component which opens a websocket connection to Binance and listens to ticker and trade blotter events

    See also https://binance-docs.github.io/apidocs/spot/en/#user-data-streams
    """

    ws_manager: BinanceWebSocketApiManager = None
    channels = ["bookTicker"]

    def __init__(self, market_data: MarketData, binance_api: BinanceApi = BinanceApi()) -> None:
        super().__init__()
        self.market_data = market_data
        self.binance_api = binance_api

    def run(self):
        self.ws_manager = BinanceWebSocketApiManager(exchange=BINANCE_WEB_SOCKET_URL)

        markets = self.binance_api.get_all_markets()
        log.info(f"Totally markets: {len(markets)}")

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
