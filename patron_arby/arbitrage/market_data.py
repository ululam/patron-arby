from typing import Dict, List, Tuple

from patron_arby.common.util import current_time_ms


class MarketData:
    data: Dict = {}
    coins: List = []
    markets: List = []
    market_paths: Dict = {}

    def __init__(self, symbol_to_base_quote_coins: Dict[str, str]) -> None:
        """
        :param symbol_to_base_quote_coins: { "BTCETH": "BTC/ETH"... }.
            This dictionary is needed to resolve ambiguities with markets (=symbols) like 'USDTUSD' (USDT/USD?
            USD/TUSD?)
        """
        super().__init__()
        coins_set = set()
        for symbol, base_quote in symbol_to_base_quote_coins.items():
            coins = base_quote.split("/")
            if len(coins) != 2:
                raise AttributeError(f"Invalid base/quote pair for symbol {symbol}: {base_quote}")
            coins_set.add(coins[0])
            coins_set.add(coins[1])
            self._add_to_market_paths(coins[0], base_quote)
            self._add_to_market_paths(coins[1], base_quote)
            self.markets.append(symbol)
        self.coins = list(coins_set)
        self.symbol_to_base_quote_coins = symbol_to_base_quote_coins

    def _add_to_market_paths(self, coin: str, market: str):
        if coin not in self.market_paths:
            self.market_paths[coin] = list()
        self.market_paths[coin].append(market)

    def put(self, data_event: Dict):
        if "data" not in data_event:
            return
        if len(self.coins) == 0:
            raise AttributeError("Coins have not been set")

        symbol, record = self._to_record(data_event)
        self.data[symbol] = record

    def get_market_paths(self):
        return self.market_paths

    def get_coins(self) -> List[str]:
        return self.coins

    def get_markets(self) -> List[str]:
        return self.markets

    def _to_record(self, data_event: Dict) -> Tuple[str, Dict]:
        data = data_event["data"]
        market = data.get("s")
        base_quote_pair = self.symbol_to_base_quote_coins.get(market)
        if not base_quote_pair:
            raise AttributeError(f"There's no mapping for symbol {market}")
        return base_quote_pair, {
            "Market": base_quote_pair,
            "BestBid": data.get("b"),
            "BestBidQuantity": data.get("B"),
            "BestAsk": data.get("a"),
            "BestAskQuantity": data.get("A"),
            "LastUpdateTimeMs": current_time_ms()
        }

    def get(self) -> Dict:
        return self.data.copy()
