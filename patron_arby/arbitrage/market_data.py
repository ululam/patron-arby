import logging
from typing import Dict, List, Optional, Set

from patron_arby.common.decorators import measure_execution_time
from patron_arby.common.ticker import Ticker
from patron_arby.common.util import current_time_ms
from patron_arby.exchange.binance.constants import Binance

log = logging.getLogger(__name__)

COINS_PATH_SEPARATOR = " -> "


class MarketData:
    data: Dict[str, Ticker] = dict()
    trading_coins: Set = set()
    markets: Set[str] = set()
    market_paths: Dict[str, Set[str]] = dict()
    # Market -> last updated time
    market_update_times: Dict = {}
    # Dict {coin 3-path => market 3-path, e.g.: "BTC -> USDT -> ETH" => "BTCUSDT -> ETHUSDT -> BTCETH"
    paths_3 = dict()
    # Dict that helps filtering coin paths by market: {"BTCUSDT" => set(all 3-paths that includes BTCUSDT as step)}
    # That is helpful when need to get all paths to check arbitrage after market ticker arrives
    market_to_coinpaths: Dict[str, Set[str]] = dict()

    market_data_update_listeners = set()

    @measure_execution_time
    def __init__(self, symbol_to_base_quote_coins: Dict[str, str], only_coins: Set = None) -> None:
        """
        :param symbol_to_base_quote_coins: { "BTCETH": "BTC/ETH"... }.
            This dictionary is needed to resolve ambiguities with markets (=symbols) like 'USDTUSD' (USDT/USD?
            USD/TUSD?)
        :param only_coins If not None, only coins find in this set are considered. All other information is dropped.
                        If None, all coins are included
        """
        super().__init__()
        if only_coins:
            log.info(f"Only considering the following coins: {sorted(list(only_coins))}")
        else:
            log.warning("Trading coins are not limited, will consider ALL coins")

        coins_set = set()
        for symbol, base_quote in symbol_to_base_quote_coins.items():
            coins = base_quote.split("/")
            if len(coins) != 2:
                raise AttributeError(f"Invalid base/quote pair for symbol {symbol}: {base_quote}")
            if only_coins and (coins[0] not in only_coins or coins[1] not in only_coins):
                # Skip coins which are not in the limitation set, if that set is specifeid
                continue
            coins_set.add(coins[0])
            coins_set.add(coins[1])
            self._add_to_market_paths(coins[0], base_quote)
            self._add_to_market_paths(coins[1], base_quote)
            self.markets.add(symbol)
        self.symbol_to_base_quote_coins = symbol_to_base_quote_coins
        self.trading_coins = coins_set

        log.info(f"Total coins: {len(self.trading_coins)}. Total markets (symbols): {len(self.markets)}")
        self._unfold_all_possible_3_paths()

    def put(self, ticker: Ticker):
        if len(self.trading_coins) == 0:
            raise AttributeError("Coins have not been set")

        base_quote_pair = self.symbol_to_base_quote_coins.get(ticker.market)
        if not base_quote_pair:
            raise AttributeError(f"There's no mapping for symbol {ticker.market}")

        ticker.market = base_quote_pair

        if not self._is_in_trading_coins(ticker.market):
            log.fine(f"Skipping {ticker.market} update as its not in trading coins")
            return

        self.data[ticker.market] = ticker
        self.market_update_times[ticker.market] = current_time_ms()

    def get_coins(self) -> List[str]:
        return list(self.trading_coins)

    def get_markets(self) -> List[str]:
        return list(self.markets)

    def get_market_last_update_time_ms(self, market: str):
        last_update_time = self.market_update_times.get(market)
        return last_update_time if last_update_time else 0

    def get_coin_price_in_usd(self, coin: str) -> Optional[float]:
        # todo Should be exchange specific
        for usd in Binance.USD_COINS:
            ticker = self.data.get(f"{coin}/{usd}")
            if ticker:
                return ticker.best_bid
            ticker = self.data.get(f"{usd}/{coin}")
            if ticker:
                return 1 / ticker.best_ask

    def filter_path3_by_markets(self, markets: Set[str]) -> List:
        filtered_coin_paths = set()
        for m in markets:
            market_key = m.replace("/", "").upper()
            coinpaths = self.market_to_coinpaths.get(market_key)
            if coinpaths:
                filtered_coin_paths |= coinpaths
        return [(coins_path, markets_path) for coins_path, markets_path in self.paths_3.items() if
                coins_path in filtered_coin_paths]

    def _add_to_market_paths(self, coin: str, market: str):
        if coin not in self.market_paths:
            self.market_paths[coin] = set()
        self.market_paths[coin].add(market)

    def _unfold_all_possible_3_paths(self):
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
                            coin_path = COINS_PATH_SEPARATOR.join([coin_a, coin_b, coin_c, coin_a])   # A -> B -> C -> A
                            market_path = COINS_PATH_SEPARATOR.join([market_ba, market_cb, market_ac])  # AB -> BC -> CA
                            self.paths_3[coin_path] = market_path
                            self._register_in_market_to_coinpath(market_ba, coin_path)
                            self._register_in_market_to_coinpath(market_cb, coin_path)
                            self._register_in_market_to_coinpath(market_ac, coin_path)

        log.info(f"Total 3-paths: {len(self.paths_3)}")

    def _register_in_market_to_coinpath(self, market: str, coin_path: str):
        market_ticker = market.replace("/", "")
        coinpaths_by_market = self.market_to_coinpaths.get(market_ticker)
        if not coinpaths_by_market:
            coinpaths_by_market = set()
            self.market_to_coinpaths[market_ticker] = coinpaths_by_market
        coinpaths_by_market.add(coin_path)

    def _path(self, *elements):
        return COINS_PATH_SEPARATOR.join(elements)

    def _get_next_coin(self, market: str, prev_coin: str):
        base_quote = market.split("/")
        next_coin = base_quote[0] if prev_coin == base_quote[1] else base_quote[1]
        return next_coin

    def _is_in_trading_coins(self, base_quote_pair: str):
        if not self.trading_coins:
            return True
        coins = base_quote_pair.split("/")
        return coins[0] in self.trading_coins and coins[1] in self.trading_coins

    def get(self) -> Dict[str, Ticker]:
        return self.data.copy()
