import time
from unittest import TestCase

from patron_arby.common.chain import AChain, AChainStep
from patron_arby.common.order import OrderSide
from patron_arby.trade.recent_arbitragers_filter import RecentArbitragersFilter


class TestRecentArbitragersFilter(TestCase):
    def test__same_chain_twice(self):
        # 1. Arrange
        filter = RecentArbitragersFilter(10_000)
        chain = AChain("BTC", [], roi=0.01)
        # 2. Act
        contains = filter.register_and_return_contained(chain)
        # 3. Assert
        self.assertFalse(contains)
        # And now, it should contain already
        self.assertTrue(filter.register_and_return_contained(chain))

    def test__duplicated_chains(self):
        # 1. Arrange
        filter = RecentArbitragersFilter(10_000)
        chain = AChain("BTC", [AChainStep("BTCUDF", OrderSide.SELL, 123, 123)], roi=0.01, profit=123)
        chain2 = AChain("BTC", [AChainStep("BTCUDF", OrderSide.SELL, 123, 123)], roi=0.01, profit=324)
        # 2. Act
        filter.register_and_return_contained(chain)
        # 3. Assert
        # And now, it should contain already
        self.assertTrue(filter.register_and_return_contained(chain2))

    def test__duplicated_chains_expiration(self):
        # 1. Arrange
        filter = RecentArbitragersFilter(1)
        chain = AChain("BTC", [AChainStep("BTCUDF", OrderSide.SELL, 123, 123)], roi=0.01, profit=123)
        # 2. Act
        filter.register_and_return_contained(chain)
        time.sleep(0.01)
        # 3. Assert
        # And now, it should be expired
        self.assertFalse(filter.register_and_return_contained(chain))
