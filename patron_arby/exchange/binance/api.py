import logging
from decimal import Decimal
from typing import Dict, List

from binance.client import Client

from patron_arby.settings import BINANCE_API_KEY, BINANCE_API_SECRET, BINANCE_API_URL

log = logging.getLogger(__name__)

# 8 digits precision in prices and quantities
QUANTIZE_PATTERN = Decimal("1.00000000")


class BinanceApi:
    def __init__(self, api_key: str = BINANCE_API_KEY, api_secret: str = BINANCE_API_SECRET) -> None:
        self.client = Client(api_key, api_secret)
        self.client.API_URL = BINANCE_API_URL

    def get_exchange_info(self):
        return self.client.get_exchange_info()

    def get_symbol_to_base_quote_mapping(self) -> Dict[str, str]:
        """
        This dictionary is needed to resolve ambiguities with markets (=symbols) like 'USDTUSD' (USDT/USD? USD/TUSD?)
        :return: { "BTCETH": "BTC/ETH" }
        """
        ei = self.client.get_exchange_info()
        return {market.get('symbol'): f"{market.get('baseAsset')}/{market.get('quoteAsset')}"
                for market in ei.get("symbols")}

    def get_all_markets(self) -> List[str]:
        ei = self.client.get_exchange_info()
        return [market.get('symbol') for market in ei.get("symbols")]

    def get_trading_commissions(self):
        pass


if __name__ == '__main__':
    api = BinanceApi()
