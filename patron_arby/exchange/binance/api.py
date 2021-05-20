import logging
from decimal import Decimal
from typing import Dict, List, Optional

from binance.client import Client
from binance.enums import SIDE_BUY, SIDE_SELL

from patron_arby.common.order import Order
from patron_arby.exchange.exchange_api import ExchangeApi
from patron_arby.settings import BINANCE_API_KEY, BINANCE_API_SECRET

log = logging.getLogger(__name__)

# 8 digits precision in prices and quantities
QUANTIZE_PATTERN = Decimal("1.00000000")


class BinanceApi(ExchangeApi):
    def __init__(self, api_key: str = BINANCE_API_KEY, api_secret: str = BINANCE_API_SECRET, api_url: str = None) \
            -> None:
        self.client = Client(api_key, api_secret)
        if api_url:
            log.info(f"Setting API URL = {api_url}")
            self.client.API_URL = api_url

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

    def get_trade_fees(self) -> Dict[str, float]:
        fees = self.client.get_trade_fee()
        return {f["symbol"]: f["taker"]for f in fees["tradeFee"]}

    def get_default_trade_fee(self) -> Optional[float]:
        acc = self.client.get_account()
        commission = acc.get("takerCommission")
        return float(commission) * 0.0001

    def put_order(self, o: Order) -> Dict:
        log.debug(f"Placing order with order client id = {o.client_order_id}")
        order = self.client.order_limit(
            side=SIDE_BUY if o.is_buy() else SIDE_SELL,
            symbol=o.symbol,
            quantity=self._norm(o.quantity),
            price=self._norm(o.price),
            newClientOrderId=o.client_order_id
        )
        log.debug(f"Placed order: {order}")

        return order

    @staticmethod
    def _norm(f: float) -> Decimal:
        """
            In order to avoid floating point notation, we need to normalize numbers into decimal representation
            (1E-3 => 0.00100000)
        :param f:
        :return:
        """
        return Decimal.from_float(float(f)).quantize(QUANTIZE_PATTERN)
