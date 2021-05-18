import json
import os
from typing import List
from unittest import TestCase, skip

from patron_arby.arbitrage.market_data import MarketData
from patron_arby.config.base import ARBITRAGE_COINS


class TestMarketData(TestCase):
    @skip
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
