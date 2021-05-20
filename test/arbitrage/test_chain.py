import json
from unittest import TestCase

from patron_arby.common.chain import AChain, AChainStep, OrderSide


class TestArbitrageChain(TestCase):
    def test__two_chains_created_in_different_time_are_different(self):
        # 1. Arrange
        # 1. Arrange
        steps = [
            AChainStep("BTCUSD", OrderSide.BUY, 0.01, 0.1),
            AChainStep("BTCETH", OrderSide.SELL, 0.02, 0.2),
        ]
        ac1 = AChain("BTC", steps, 0.001, 0.3)
        ac2 = AChain("BTC", steps, 0.001, 0.3)
        # 2. Act
        ac2.timems = ac1.timems + 1
        # 3. Assert
        self.assertNotEqual(ac1.uid(), ac2.uid())

    def test__two_same_chains_are_of_same_path(self):
        # 1. Arrange
        steps = [
            AChainStep("BTCUSD", OrderSide.BUY, 0.01, 0.1),
            AChainStep("BTCETH", OrderSide.SELL, 0.02, 0.2),
        ]
        ac1 = AChain("BTC", steps, 0.001, 0.3)
        ac2 = AChain("BTC", steps, 0.001, 0.3)
        # 3. Assert
        self.assertTrue(ac1.is_for_same_chain(ac2))
        self.assertTrue(ac2.is_for_same_chain(ac1))
        self.assertTrue(ac1.is_for_same_chain(ac1))

    def test__chain_to_json(self):
        # 1. Arrange
        steps = [
            AChainStep("BTCUSD", OrderSide.BUY, 0.01, 0.1),
            AChainStep("BTCETH", OrderSide.SELL, 0.02, 0.2),
        ]
        ac1 = AChain("BTC", steps, 0.001, 0.3)
        # 2. Act
        json_str = json.dumps(ac1.to_dict())
        ac2 = AChain.from_dict(json.loads(json_str))
        # 3. Assert
        print(ac1)
        print(ac2)
        self.assertEqual(ac1, ac2)

    def test___get_what_we_propose_volume__buy_step(self):
        step = AChainStep("BTCUSDT", OrderSide.BUY, 50_000, 3)
        we_propose_volume = step.get_what_we_propose_volume()
        eq(150_000, we_propose_volume)        # We give 150_000 USD

    def test___get_what_we_propose_volume__sell_step(self):
        step = AChainStep("BTCUSDT", OrderSide.SELL, 50_000, 3)
        we_propose_volume = step.get_what_we_propose_volume()
        eq(3, we_propose_volume)        # We give 3 BTC

    def test__get_what_we_get_volume__buy_step(self):
        step = AChainStep("ETHBTC", OrderSide.BUY, 0.05, 40)
        we_get_volume = step.get_what_we_get_volume()
        eq(40, we_get_volume)        # We get 40 ETH

    def test__get_what_we_get_volume__sell_step(self):
        step = AChainStep("ETHBTC", OrderSide.SELL, 0.05, 40)
        we_get_volume = step.get_what_we_get_volume()
        eq(2, we_get_volume)         # We get 2 BTC


def eq(f1: float, f2: float):
    if abs(f1 - f2) <= 0.0000001:
        return True
    raise AssertionError(f"{f1} != {f2}")
