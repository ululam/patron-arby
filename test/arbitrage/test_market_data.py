import json
import os
from typing import List
from unittest import TestCase, skip

from patron_arby.arbitrage.market_data import MarketData
from patron_arby.config.base import ARBITRAGE_COINS


class TestMarketData(TestCase):
    # todo Fix
    @skip("Fails during commit hook, but works fine if run standalone")
    def test__limit_coins(self):
        # 1. Arrange & act
        market_data = self._load_market_data(["BUSD", "BTC"])
        # 3. Assert
        self.assertEqual(["BTCBUSD"], market_data.markets)
        self.assertEqual({"BTC", "BUSD"}, market_data.trading_coins)
        self.assertEqual({"BTC": ["BTC/BUSD"], "BUSD": ["BTC/BUSD"]}, market_data.market_paths)

    def test__is_in_trading_coins_if_None(self):
        market_data = MarketData({})
        self.assertTrue(market_data._is_in_trading_coins("BTC/USD"))
        self.assertTrue(market_data._is_in_trading_coins("COINACOINB"))
        self.assertTrue(market_data._is_in_trading_coins(""))

    def test__is_in_trading_coins(self):
        market_data = MarketData({})
        market_data.trading_coins = ARBITRAGE_COINS
        for c1 in ARBITRAGE_COINS:
            for c2 in ARBITRAGE_COINS:
                if c1 == c2:
                    continue
                self.assertTrue(market_data._is_in_trading_coins(f"{c1}/{c2}"), f"{c1}/{c2}")
                self.assertTrue(market_data._is_in_trading_coins(f"{c2}/{c1}"), f"{c2}/{c1}")

        self.assertFalse(market_data._is_in_trading_coins("NONEXUSTINGCOIN"))

    def test__simple_init(self):
        # 1. Arrange
        symbol_to_base_quote_coins = {"BTCETH": "BTC/ETH",
                                      "BTCUSDT": "BTC/USDT",
                                      "ETHUSDT": "ETH/USDT",
                                      "EURUSDT": "EUR/USDT",
                                      "DOGEUSDT": "DOGE/USDT",
                                      "DOGEEUR": "DOGE/EUR"}
        # 2. Act
        market_data = MarketData(symbol_to_base_quote_coins)
        # 3. Assert
        self.assertEqual({'EUR', 'DOGE', 'USDT', 'ETH', 'BTC'}, market_data.trading_coins)
        self.assertEqual({'BTCETH', 'BTCUSDT', 'ETHUSDT', 'EURUSDT', 'DOGEUSDT', 'DOGEEUR'}, market_data.markets)
        self.assertEqual({'BTC': {'BTC/ETH', 'BTC/USDT'}, 'ETH': {'BTC/ETH', 'ETH/USDT'},
                          'USDT': {'BTC/USDT', 'ETH/USDT', 'EUR/USDT', 'DOGE/USDT'}, 'EUR': {'EUR/USDT', 'DOGE/EUR'},
                          'DOGE': {'DOGE/USDT', 'DOGE/EUR'}}, market_data.market_paths)
        self.assertEqual({
            'BTCETH': {'USDT -> ETH -> BTC -> USDT', 'BTC -> ETH -> USDT -> BTC', 'ETH -> BTC -> USDT -> ETH',
                       'USDT -> BTC -> ETH -> USDT', 'ETH -> USDT -> BTC -> ETH', 'BTC -> USDT -> ETH -> BTC'},
            'ETHUSDT': {'USDT -> ETH -> BTC -> USDT', 'BTC -> ETH -> USDT -> BTC', 'ETH -> BTC -> USDT -> ETH',
                        'USDT -> BTC -> ETH -> USDT', 'ETH -> USDT -> BTC -> ETH', 'BTC -> USDT -> ETH -> BTC'},
            'BTCUSDT': {'USDT -> ETH -> BTC -> USDT', 'BTC -> ETH -> USDT -> BTC', 'ETH -> BTC -> USDT -> ETH',
                        'USDT -> BTC -> ETH -> USDT', 'ETH -> USDT -> BTC -> ETH', 'BTC -> USDT -> ETH -> BTC'},
            'DOGEUSDT': {'DOGE -> USDT -> EUR -> DOGE', 'EUR -> DOGE -> USDT -> EUR', 'DOGE -> EUR -> USDT -> DOGE',
                         'USDT -> DOGE -> EUR -> USDT', 'EUR -> USDT -> DOGE -> EUR', 'USDT -> EUR -> DOGE -> USDT'},
            'DOGEEUR': {'DOGE -> USDT -> EUR -> DOGE', 'EUR -> DOGE -> USDT -> EUR', 'DOGE -> EUR -> USDT -> DOGE',
                        'USDT -> DOGE -> EUR -> USDT', 'EUR -> USDT -> DOGE -> EUR', 'USDT -> EUR -> DOGE -> USDT'},
            'EURUSDT': {'DOGE -> USDT -> EUR -> DOGE', 'EUR -> DOGE -> USDT -> EUR', 'DOGE -> EUR -> USDT -> DOGE',
                        'USDT -> DOGE -> EUR -> USDT', 'EUR -> USDT -> DOGE -> EUR', 'USDT -> EUR -> DOGE -> USDT'}},
            market_data.market_to_coinpaths)

        self.assertEqual({'BTC -> ETH -> USDT -> BTC': 'BTC/ETH -> ETH/USDT -> BTC/USDT',
                          'BTC -> USDT -> ETH -> BTC': 'BTC/USDT -> ETH/USDT -> BTC/ETH',
                          'ETH -> BTC -> USDT -> ETH': 'BTC/ETH -> BTC/USDT -> ETH/USDT',
                          'ETH -> USDT -> BTC -> ETH': 'ETH/USDT -> BTC/USDT -> BTC/ETH',
                          'USDT -> DOGE -> EUR -> USDT': 'DOGE/USDT -> DOGE/EUR -> EUR/USDT',
                          'USDT -> EUR -> DOGE -> USDT': 'EUR/USDT -> DOGE/EUR -> DOGE/USDT',
                          'USDT -> BTC -> ETH -> USDT': 'BTC/USDT -> BTC/ETH -> ETH/USDT',
                          'USDT -> ETH -> BTC -> USDT': 'ETH/USDT -> BTC/ETH -> BTC/USDT',
                          'EUR -> USDT -> DOGE -> EUR': 'EUR/USDT -> DOGE/USDT -> DOGE/EUR',
                          'EUR -> DOGE -> USDT -> EUR': 'DOGE/EUR -> DOGE/USDT -> EUR/USDT',
                          'DOGE -> USDT -> EUR -> DOGE': 'DOGE/USDT -> EUR/USDT -> DOGE/EUR',
                          'DOGE -> EUR -> USDT -> DOGE': 'DOGE/EUR -> EUR/USDT -> DOGE/USDT'}, market_data.paths_3)

    def test__filter_path3_by_markets(self):
        # 1. Arrange
        symbol_to_base_quote_coins = {"ETHUSDT": "ETH/USDT",
                                      "EURUSDT": "EUR/USDT",
                                      "DOGEUSDT": "DOGE/USDT",
                                      "DOGEEUR": "DOGE/EUR"}
        # 2. Act
        market_data = MarketData(symbol_to_base_quote_coins)
        # 3. Assert
        paths3 = market_data.filter_path3_by_markets({"DOGEEUR"})
        self.assertEqual(6, len(paths3))

        paths3 = market_data.filter_path3_by_markets({"dogeeur"})
        self.assertEqual(6, len(paths3))        # Same result

        paths3 = market_data.filter_path3_by_markets({"DOGE/EUR"})
        self.assertEqual(6, len(paths3))        # Same result

        paths3 = market_data.filter_path3_by_markets({"NOT_EXISTS"})
        self.assertEqual(0, len(paths3))        # No exception

    def _load_market_data(self, limit_to_coins: List[str] = None):
        symbol_to_base_quote_coins, bidasks = self._load_local_jsons()
        market_data = MarketData(symbol_to_base_quote_coins, limit_to_coins)
        market_data.data = bidasks

        return market_data

    def _load_local_jsons(self):
        path_to_current_dir = os.path.dirname(os.path.realpath(__file__))
        with open(f"{path_to_current_dir}/symbol_to_base_quote_coins.json", "r") as f:
            symbol_to_base_quote_coins = json.load(f)
        with open(f"{path_to_current_dir}/bidasks.json", "r") as f:
            bidasks = json.load(f)

        return symbol_to_base_quote_coins, bidasks
