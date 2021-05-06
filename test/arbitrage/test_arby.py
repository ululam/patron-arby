import json
import logging
import os
from unittest import TestCase

from patron_arby.arbitrage.arby import PetroniusArbiter
from patron_arby.arbitrage.market_data import MarketData

log = logging.getLogger(__name__)


class TestArby(TestCase):
    def test__get_coin_price_in_another_coin_forward(self):
        # 1. Arrange
        bidask = {
            "Market": "BTC/USDT",
            "BestBid": 55100,
            "BestBidQuantity": 1.22,
            "BestAsk": 55200,
            "BestAskQuantity": 2.01
        }

        # 2. Act
        price, quantity = PetroniusArbiter._get_coin_price_and_quantity_in_another_coin(bidask, "BTC")
        log.debug(f"I can buy {quantity} BTC for USDT at the price {price}")
        log.debug(f"This is equivalent to BUY {bidask.get('BestAskQuantity')} BTC at the price {bidask.get('BestAsk')} "
              f"for 1 BTC")

        # 3. Assert
        self.assertEqual(55200, price)
        self.assertEqual(2.01, quantity)

    def test__get_coin_price_in_another_coin_reverse(self):
        # 1. Arrange
        bidask = {
            "Market": "BTC/USDT",
            "BestBid": 55100,
            "BestBidQuantity": 1.22,
            "BestAsk": 55200,
            "BestAskQuantity": 2.01
        }

        # 2. Act
        price, quantity = PetroniusArbiter._get_coin_price_and_quantity_in_another_coin(bidask, "USDT")
        log.debug(f"I can buy {quantity} USDT for BTC at the price {price}")
        log.debug(f"This is equivalent to SELL {bidask.get('BestBidQuantity')} BTC at the price {bidask.get('BestBid')} "
              f"for 1 BTC")
        # 3. Assert
        self.assertEqual(1 / 55100, price)
        self.assertEqual(55100 * 1.22, quantity)

    def test__cyclic_buy_sell_same_market_decrease_amount(self):
        # 1. Arrange
        bidask = {
            "Market": "BTC/USDT",
            "BestBid": 55100,
            "BestBidQuantity": 1.22,
            "BestAsk": 55200,
            "BestAskQuantity": 2.01
        }

        btc_amount = 1

        # 2. Act
        price_btc, quantity_btc = PetroniusArbiter._get_coin_price_and_quantity_in_another_coin(bidask, "BTC")
        price_usdt, quantity_usdt = PetroniusArbiter._get_coin_price_and_quantity_in_another_coin(bidask, "USDT")

        # 3. Assert
        btc_amount_after_buy_sell = (btc_amount / price_usdt) / price_btc
        self.assertLess(btc_amount_after_buy_sell, btc_amount)

    def test__find_using_real_market_snapshot(self):
        # 1. Arrange
        arby = PetroniusArbiter(self._load_market_data())

        # 2. Act
        result = arby.find()

        result.sort(key=lambda val: -float(val.get("roi")))
        print(result)

        # 3. Assert
        # no exceptions

    def _load_market_data(self):
        path_to_current_dir = os.path.dirname(os.path.realpath(__file__))
        with open(f"{path_to_current_dir}/symbol_to_base_quote_coins.json", "r") as f:
            symbol_to_base_quote_coins = json.load(f)
        market_data = MarketData(symbol_to_base_quote_coins)

        with open(f"{path_to_current_dir}/bidasks.json", "r") as f:
            market_data.data = json.load(f)

        return market_data
