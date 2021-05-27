from typing import Dict

from patron_arby.common.ticker import Ticker
from patron_arby.exchange.exchange_ticker_converter import ExchangeTickerConverter


class BinanceTickerConverter(ExchangeTickerConverter):
    def from_ws_event(self, ticker_event: Dict) -> Ticker:
        data = ticker_event["data"]
        return Ticker(market=data.get("s"),
            best_bid=float(data.get("b")), best_bid_quantity=float(data.get("B")),
            best_ask=float(data.get("a")), best_ask_quantity=float(data.get("A")))
