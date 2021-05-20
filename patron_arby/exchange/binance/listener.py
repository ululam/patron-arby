import json
import logging
import math
from typing import Dict, List, Set, Union

from unicorn_binance_websocket_api.unicorn_binance_websocket_api_manager import (
    BinanceWebSocketApiManager,
)

from patron_arby.arbitrage.market_data import MarketData
from patron_arby.db.keys_provider import KeysProvider
from patron_arby.exchange.binance.constants import Binance
from patron_arby.exchange.exchange_event_listener import ExchangeEventListener
from patron_arby.settings import BINANCE_WEB_SOCKET_URL

log = logging.getLogger(__name__)


class BinanceDataListener:
    """
    Component which opens a websocket connection to Binance and listens to ticker and trade blotter events

    See also https://binance-docs.github.io/apidocs/spot/en/#user-data-streams
    """

    ws_manager: BinanceWebSocketApiManager = None
    channels = ["bookTicker"]
    event_listeners: Set[ExchangeEventListener] = set()

    # Todo Replace MarketData with Bus
    def __init__(self, market_data: MarketData, keys_provider: KeysProvider, markets: Set[str]) -> None:
        super().__init__()
        self.market_data = market_data
        self.keys_provider = keys_provider
        self.markets = markets

    def run(self):
        self.ws_manager = BinanceWebSocketApiManager(exchange=BINANCE_WEB_SOCKET_URL)

        log.info(f"Totally markets: {len(self.markets)}")

        self._create_streams(list(self.markets))
        self._create_account_stream()

        while True:
            oldest_stream_data_from_stream_buffer = (
                self.ws_manager.pop_stream_data_from_stream_buffer()
            )
            if not oldest_stream_data_from_stream_buffer:
                continue

            ticker_event = self._to_dict(oldest_stream_data_from_stream_buffer)
            if not ticker_event:
                continue

            for el in self.event_listeners:
                el.on_exchange_event(ticker_event)

            self.market_data.put(ticker_event)

    def add_event_listener(self, el: ExchangeEventListener):
        self.event_listeners.add(el)

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

    def _create_account_stream(self):
        binance_api_key, binance_api_secret = self.keys_provider.get_exchange_api_keys(Binance.NAME)
        self.ws_manager.create_stream(
            ["!userData"],
            ["arr"],  # Means "single stream for all"
            api_key=binance_api_key,
            api_secret=binance_api_secret,
            stream_label="user_data"
        )

    @staticmethod
    def _to_dict(stream_event) -> Union[Dict, None]:
        try:
            event = json.loads(stream_event)
            return event
        except Exception as e:
            log.error(f"Error during filtering event {stream_event}", exc_info=e)
        return None
