import logging
from typing import Dict, List, Tuple

from patron_arby.common.decorators import log_execution_time
from patron_arby.common.util import current_time_ms

log = logging.getLogger(__name__)

COINS_PATH_SEPARATOR = " -> "


class MarketData:
    data: Dict = {}
    coins: List = []
    markets: List = []
    market_paths: Dict = {}
    # Market -> last updated time
    market_update_times: Dict = {}

    @log_execution_time
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

        log.info(f"Total coins: {len(self.coins)}. Total markets (symbols): {len(self.markets)}")
        self._unfold_all_possible_3_paths()

    def _add_to_market_paths(self, coin: str, market: str):
        if coin not in self.market_paths:
            self.market_paths[coin] = list()
        self.market_paths[coin].append(market)

    def _unfold_all_possible_3_paths(self):
        self.paths_3 = dict()
        for coin_a, markets_ba in self.market_paths.items():
            for market_ba in markets_ba:
                coin_b = self._get_next_coin(market_ba, coin_a)
                if coin_b == coin_a:
                    continue
                for market_cb in self.market_paths.get(coin_b):
                    coin_c = self._get_next_coin(market_cb, coin_b)
                    if coin_c == coin_b or coin_b == coin_a:
                        continue
                    for market_ac in self.market_paths.get(coin_c):
                        coin_d = self._get_next_coin(market_ac, coin_c)
                        if coin_d == coin_a:
                            self.paths_3[f"{coin_a} -> {coin_b} -> {coin_c} -> {coin_a}"] = \
                                f"{market_ba} -> {market_cb} -> {market_ac}"
                            # self.paths_3[self._path(coin_a, coin_b, coin_c, coin_a)] = \
                            #     self._path(markets_ba, market_cb, market_ac)

        log.info(f"Total 3-paths: {len(self.paths_3)}")

    def _path(self, *elements):
        return COINS_PATH_SEPARATOR.join(elements)

    def _get_next_coin(self, market: str, prev_coin: str):
        base_quote = market.split("/")
        next_coin = base_quote[0] if prev_coin == base_quote[1] else base_quote[1]
        return next_coin

    def put(self, data_event: Dict):
        if "data" not in data_event:
            return
        if len(self.coins) == 0:
            raise AttributeError("Coins have not been set")

        symbol, record = self._to_record(data_event)
        self.data[symbol] = record
        self.market_update_times[symbol] = current_time_ms()

    def get_market_paths_only_updated_since(self, since_time_ms: int):
        """
        :return: Dictionary of only those market paths which have been updated since given time
        """
        return self.market_paths

    def get_coins(self) -> List[str]:
        return self.coins

    def get_markets(self) -> List[str]:
        return self.markets

    def get_market_last_update_time_ms(self, market: str):
        last_update_time = self.market_update_times.get(market)
        return last_update_time if last_update_time else 0

    def _to_record(self, data_event: Dict) -> Tuple[str, Dict]:
        data = data_event["data"]
        market = data.get("s")
        base_quote_pair = self.symbol_to_base_quote_coins.get(market)
        if not base_quote_pair:
            raise AttributeError(f"There's no mapping for symbol {market}")
        return base_quote_pair, {
            "Market": base_quote_pair,
            "BestBid": float(data.get("b")),
            "BestBidQuantity": float(data.get("B")),
            "BestAsk": float(data.get("a")),
            "BestAskQuantity": float(data.get("A")),
            "LastUpdateTimeMs": current_time_ms()
        }

    def get(self) -> Dict:
        return self.data.copy()
