from typing import Dict, Union

from patron_arby.common.exchange_limitation import ExchangeLimitation


class BinanceExchangeLimitations:
    limits: Dict[str, Dict[ExchangeLimitation, float]] = dict()

    def __init__(self, binance_exchange_info: Dict) -> None:
        super().__init__()
        self._build_exchange_limitations(binance_exchange_info)

    def get_limitations(self) -> Dict[str, Dict[ExchangeLimitation, float]]:
        return self.limits

    def _build_exchange_limitations(self, binance_exchange_info: Dict):
        for s in binance_exchange_info.get('symbols'):
            market = s.get("symbol")
            market_dict = dict()
            filters = s.get("filters")
            for f in filters:
                if f.get("filterType") == "PRICE_FILTER":
                    market_dict[ExchangeLimitation.MIN_PRICE_STEP] = self._get_value(f, "tickSize")
                elif f.get("filterType") == "LOT_SIZE":
                    market_dict[ExchangeLimitation.MIN_VOLUME_STEP] = self._get_value(f, "stepSize")
                elif f.get("filterType") == "MIN_NOTIONAL":
                    # Min notional is set in base coin (e.g. BTCBUSD: 10 => 10 BUSD)
                    market_dict[ExchangeLimitation.MIN_NOTIONAL] = self._get_value(f, "minNotional")
            self.limits[market] = market_dict

    def _get_value(self, f: Dict, key: str):
        return float(self._remote_trailing_zeros(f.get(key)))

    @staticmethod
    def _remote_trailing_zeros(str_float: Union[str, float]) -> str:
        return str(float(str_float))
