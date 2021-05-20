from unittest import TestCase, skip

from patron_arby.arbitrage.arby_utils import ArbyUtils
from patron_arby.common.chain import AChainStep
from patron_arby.common.order import OrderSide


class TestArbyUtils(TestCase):

    def test___get_what_we_propose_volume__buy_step(self):
        step = AChainStep("BTCUSDT", OrderSide.BUY, 50_000, 3)
        we_propose_volume = ArbyUtils._get_what_we_propose_volume(step)
        eq(150_000, we_propose_volume)        # We give 150_000 USD

    def test___get_what_we_propose_volume__sell_step(self):
        step = AChainStep("BTCUSDT", OrderSide.SELL, 50_000, 3)
        we_propose_volume = ArbyUtils._get_what_we_propose_volume(step)
        eq(3, we_propose_volume)        # We give 3 BTC

    def test__get_what_we_get_volume__buy_step(self):
        step = AChainStep("ETHBTC", OrderSide.BUY, 0.05, 40)
        we_get_volume = ArbyUtils._get_what_we_get_volume(step)
        eq(40, we_get_volume)        # We get 40 ETH

    def test__get_what_we_get_volume__sell_step(self):
        step = AChainStep("ETHBTC", OrderSide.SELL, 0.05, 40)
        we_get_volume = ArbyUtils._get_what_we_get_volume(step)
        eq(2, we_get_volume)         # We get 2 BTC

    def test__calc_and_set_max_available_triangle_volume__all_buys(self):
        # 1. Arrange
        step1 = AChainStep("BTCUSDT", OrderSide.BUY, 50_000, 2)
        step2 = AChainStep("ETHBTC", OrderSide.BUY, 0.05, 42)
        step3 = AChainStep("USDTETH", OrderSide.BUY, 0.0004, 300_000)       # Ok there's no such a market, but for test
        # 2. Act
        step1, step2, step3 = ArbyUtils.calc_and_return_max_available_triangle_volume(step1, step2, step3)
        # 3. Assert
        eq(2, step1.volume)
        eq(40, step2.volume)
        eq(100_000, step3.volume)

    @skip
    def test__calc_and_set_max_available_triangle_volume__2sell_1buy(self):
        pass

    def test__calc_and_set_max_available_triangle_volume__2buy_1sell(self):
        # 1. Arrange
        step1 = AChainStep("BTCUSDT", OrderSide.BUY, 50_000, 2)
        step2 = AChainStep("ETHBTC", OrderSide.BUY, 0.05, 42)
        step3 = AChainStep("ETHUSDT", OrderSide.SELL, 2500, 40)
        # 2. Act
        step1, step2, step3 = ArbyUtils.calc_and_return_max_available_triangle_volume(step1, step2, step3)
        # 3. Assert
        eq(2, step1.volume)
        eq(40, step2.volume)
        eq(40, step3.volume)

    def test__calc_and_set_max_available_triangle_volume__all_sells(self):
        # 1. Arrange
        step1 = AChainStep("AB", OrderSide.SELL, 10, 2)         # -> 20B for 2A
        step2 = AChainStep("BC", OrderSide.SELL, 0.1, 21)       # -> 2.1C for 20B
        step3 = AChainStep("CA", OrderSide.SELL, 0.99, 2.2)     # -> 2.178A for 2.2C
        # 2. Act
        step1, step2, step3 = ArbyUtils.calc_and_return_max_available_triangle_volume(step1, step2, step3)
        # 3. Assert
        eq(2, step1.volume)
        eq(20, step2.volume)
        eq(2, step3.volume)   # yeas, negative arbitrage

    def test__calc_and_set_max_available_triangle_volume__3buys_min_at_step_1(self):
        pass

    def test__calc_and_set_max_available_triangle_volume__3buys_min_at_step_2(self):
        pass

    def test__calc_and_set_max_available_triangle_volume__3buys_min_at_step_3(self):
        pass

    def test__calc_and_set_max_available_triangle_volume__3sells_min_at_step_1(self):
        # 1. Arrange
        step1 = AChainStep("AB", OrderSide.SELL, 10, 2)     # -> 20B for 2A
        step2 = AChainStep("BC", OrderSide.SELL, 0.1, 21)    # -> 2.1C for 21B
        step3 = AChainStep("AC", OrderSide.SELL, 1.1, 2.1)      # -> 2.21A for 2.1C
        # 2. Act
        step1, step2, step3 = ArbyUtils.calc_and_return_max_available_triangle_volume(step1, step2, step3)
        # 3. Assert
        eq(2, step1.volume)
        eq(20, step2.volume)
        eq(2, step3.volume)

    def test__calc_and_set_max_available_triangle_volume__3sells_min_at_step_2(self):
        # 1. Arrange
        step1 = AChainStep("AB", OrderSide.SELL, 10, 2)     # -> 20B for 2A
        step2 = AChainStep("BC", OrderSide.SELL, 0.1, 19)    # -> 1.9C for 19B
        step3 = AChainStep("AC", OrderSide.SELL, 1.1, 2.1)   # -> 2.21A for 2.1C
        # 2. Act
        step1, step2, step3 = ArbyUtils.calc_and_return_max_available_triangle_volume(step1, step2, step3)
        # 3. Assert
        eq(1.9, step1.volume)
        eq(19, step2.volume)
        eq(1.9, step3.volume)

    def test__calc_and_set_max_available_triangle_volume__3sells_min_at_step_3(self):
        # 1. Arrange
        step1 = AChainStep("AB", OrderSide.SELL, 10, 2)     # -> 20B for 2A
        step2 = AChainStep("BC", OrderSide.SELL, 0.1, 20)    # -> 2C for 20B
        step3 = AChainStep("AC", OrderSide.SELL, 1.1, 1.8)   # -> 1.98A for 1.8C
        # 2. Act
        step1, step2, step3 = ArbyUtils.calc_and_return_max_available_triangle_volume(step1, step2, step3)
        # 3. Assert
        eq(1.8, step1.volume)
        eq(18, step2.volume)
        eq(1.8, step3.volume)

    def test__calc_and_set_max_available_triangle_volume__corner_case1(self):
        # 1. Arrange
        step1 = AChainStep("BTCUSDT", OrderSide.BUY, 50_000, 0)
        step2 = AChainStep("ETHBTC", OrderSide.BUY, 0.05, 42)
        step3 = AChainStep("ETHUSDT", OrderSide.SELL, 2500, 40)
        # 2. Act
        step1, step2, step3 = ArbyUtils.calc_and_return_max_available_triangle_volume(step1, step2, step3)
        # 3. Assert
        eq(0, step1.volume)
        eq(0, step2.volume)
        eq(0, step3.volume)


def eq(f1: float, f2: float):
    if abs(f1 - f2) <= 0.0000001:
        return True
    raise AssertionError(f"{f1} != {f2}")
