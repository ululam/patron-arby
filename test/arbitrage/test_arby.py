import json
from typing import List
from unittest import TestCase, skip

from patron_arby.arbitrage.arby import PetroniusArbiter
from patron_arby.arbitrage.market_data import MarketData
from patron_arby.settings import *

log = logging.getLogger(__name__)


class TestArby(TestCase):
    def test__get_coin_price_in_another_coin_forward__no_commission(self):
        # 1. Arrange
        bidask = {
            "Market": "BTC/USDT",
            "BestBid": 55100,
            "BestBidQuantity": 1.22,
            "BestAsk": 55200,
            "BestAskQuantity": 2.01
        }
        arby = PetroniusArbiter(MarketData(dict()), {}, 0)
        # 2. Act
        step = arby._get_coin_price_and_quantity_in_another_coin(bidask, "BTC")
        print(f"I can buy {step.volume} BTC for USDT at the price {step.price}")
        print(f"This is equivalent to BUY {bidask.get('BestAskQuantity')} BTC at the price {bidask.get('BestAsk')} "
              f"for 1 BTC")

        # 3. Assert
        self.assertEqual(55200, step.price)
        self.assertEqual(2.01, step.volume)

    def test__get_coin_price_in_another_coin_reverse__no_commission(self):
        # 1. Arrange
        bidask = {
            "Market": "BTC/USDT",
            "BestBid": 55100,
            "BestBidQuantity": 1.22,
            "BestAsk": 55200,
            "BestAskQuantity": 2.01
        }
        arby = PetroniusArbiter(MarketData(dict()), {}, 0)
        # 2. Act
        step = arby._get_coin_price_and_quantity_in_another_coin(bidask, "USDT")
        log.debug(f"I can buy {step.volume} USDT for BTC at the price {step.price}")
        log.debug(f"This is equivalent to SELL {bidask.get('BestBidQuantity')} BTC at the price {bidask.get('BestBid')} "
              f"for 1 BTC")
        # 3. Assert
        self.assertEqual(55100, step.price)
        self.assertEqual(55100 * 1.22, step.volume)

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
        arby = PetroniusArbiter(MarketData(dict()), {})

        # 2. Act
        step_btc = arby._get_coin_price_and_quantity_in_another_coin(bidask, "BTC")
        step_usdt = arby._get_coin_price_and_quantity_in_another_coin(bidask, "USDT")

        # 3. Assert
        btc_amount_after_buy_sell = (btc_amount / step_usdt.price) / step_btc.price
        self.assertLess(btc_amount_after_buy_sell, btc_amount)

    def test__trade_fees(self):
        # 1. Arrange
        bidask = {
            "Market": "BTC/USDT",
            "BestBid": 50000,
            "BestBidQuantity": 1.22,
            "BestAsk": 60000,
            "BestAskQuantity": 2.01
        }
        btc_amount = 1
        arby = PetroniusArbiter(MarketData(dict()), {bidask.get("Market").replace("/", ""): 0.1})

        # 2. Act
        step_btc = arby._get_coin_price_and_quantity_in_another_coin(bidask, "BTC")
        step_usdt = arby._get_coin_price_and_quantity_in_another_coin(bidask, "USDT")

        # 3. Assert
        self.assertEqual(bidask.get("BestAsk") * 1.1, step_btc.price)
        self.assertEqual(bidask.get("BestBid") * 0.9, step_usdt.price)

    @skip
    def test__find_using_real_market_snapshot(self):
        # 1. Arrange
        arby = PetroniusArbiter(self._load_market_data(), {})

        # 2. Act
        result = arby.find()

        result.sort(key=lambda val: -val.profit_usd)
        for r in result[:3]:
            print(r.to_user_readable())

        # 3. Assert
        # no exceptions
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
