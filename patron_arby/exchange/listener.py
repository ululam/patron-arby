import json
import logging
from typing import Dict, Union

from unicorn_binance_websocket_api.unicorn_binance_websocket_api_manager import (
    BinanceWebSocketApiManager,
)

from patron_arby.config.staging import BINANCE_API_KEY, BINANCE_API_SECRET

log = logging.getLogger(__name__)


class BinanceDataListener:
    """
    Component which opens a websocket connection to Binance and listens to ticker and trade blotter events

    See also https://binance-docs.github.io/apidocs/spot/en/#user-data-streams
    """

    ws_manager: BinanceWebSocketApiManager = None

    def run(self):
        binance_api_key, binance_api_secret = BINANCE_API_KEY, BINANCE_API_SECRET

        self.ws_manager = BinanceWebSocketApiManager(
            # todo Test/Prod mode
            exchange="binance.com-testnet"
        )

        self.ws_manager.create_stream(
            ['!miniTicker', '!ticker', '!bookTicker'],
            ["arr"],  # Means "single stream for all"
            api_key=binance_api_key,
            api_secret=binance_api_secret
        )

        while True:
            oldest_stream_data_from_stream_buffer = (
                self.ws_manager.pop_stream_data_from_stream_buffer()
            )
            if not oldest_stream_data_from_stream_buffer:
                continue

            ticker_event = self._filter_events(oldest_stream_data_from_stream_buffer)
            if not ticker_event:
                continue

            print(ticker_event)

    @staticmethod
    def _filter_events(stream_event) -> Union[Dict, None]:
        try:
            event = json.loads(stream_event)
            return event
        except Exception as e:
            log.error(f"Error during filtering event {stream_event}", exc_info=e)
        return None
