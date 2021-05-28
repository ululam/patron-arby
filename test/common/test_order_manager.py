from decimal import Decimal
from unittest import TestCase
from unittest.mock import Mock

from patron_arby.common.chain import AChain, AChainStep
from patron_arby.common.exchange_limitation import ExchangeLimitation
from patron_arby.common.order import Order, OrderSide
from patron_arby.config.base import ORDER_PROFIT_THRESHOLD_USD
from patron_arby.order.manager import OrderManager


class TestOrderManager(TestCase):
    def test__round_price_and_volume_to_market_requirements(self):
        # 1. Arrange
        limits = {"BTCUSD": {
            ExchangeLimitation.MIN_PRICE_STEP: 0.01,
            ExchangeLimitation.MIN_VOLUME_STEP: 0.001
        }}
        om = OrderManager(Mock(), limits, Mock())
        order = Order("", OrderSide.SELL, "BTCUSD", price=12.34245435, quantity=44.345945345345)
        # 2. Act
        order = om._round_price_and_volume_to_market_requirements(order)
        # 3. Assert
        self.assertEqual(Decimal("12.34"), order.price)
        self.assertEqual(Decimal("44.346"), order.quantity)

    def test__shrink_volumes_according_to_balances__simple_case(self):
        # 1. Arrange
        om = OrderManager(Mock(), {}, Mock())
        balances = {"BTC": 20, "USDT": 500, "ETH": 10}
        chain = AChain("BTC", [
            AChainStep("BTC/USDT", OrderSide.BUY, 30_000, 0.01),
            AChainStep("ETH/BTC", OrderSide.BUY, 0.05, 5),
            AChainStep("ETH/USDT", OrderSide.SELL, 2500, 5)
        ])
        # 2. Act
        chain = om._shrink_volumes_according_to_balances(chain, balances, 0.3)
        # 3. Assert
        self.assertEqual(0.005, chain.steps[0].volume)
        self.assertEqual(2.5, chain.steps[1].volume)
        self.assertEqual(2.5, chain.steps[2].volume)

    def test__shrink_volumes_according_to_balances__no_shrink_required(self):
        # 1. Arrange
        om = OrderManager(Mock(), {}, Mock())
        balances = {"BTC": 200, "USDT": 50000, "ETH": 10000}
        chain = AChain("BTC", [
            AChainStep("BTC/USDT", OrderSide.BUY, 30_000, 0.01),
            AChainStep("ETH/BTC", OrderSide.BUY, 0.05, 5),
            AChainStep("ETH/USDT", OrderSide.SELL, 2500, 5)
        ])
        # 2. Act
        chain = om._shrink_volumes_according_to_balances(chain, balances, 0.3)
        # 3. Assert
        self.assertEqual(0.01, chain.steps[0].volume)
        self.assertEqual(5, chain.steps[1].volume)
        self.assertEqual(5, chain.steps[2].volume)

    def test__shrink_volumes_according_to_balances__all_balances_unsufficient(self):
        # 1. Arrange
        om = OrderManager(Mock(), {}, Mock())
        balances = {"BTC": 0.1, "USDT": 300, "ETH": 1}
        chain = AChain("BTC", [
            AChainStep("BTC/USDT", OrderSide.BUY, 30_000, 0.01),
            AChainStep("ETH/BTC", OrderSide.BUY, 0.05, 5),
            AChainStep("ETH/USDT", OrderSide.SELL, 2500, 5)     # <- Max volume/balance factor
        ])
        # 2. Act
        chain = om._shrink_volumes_according_to_balances(chain, balances, 0.3)
        # 3. Assert
        self.assertEqual(0.0006, chain.steps[0].volume)
        self.assertEqual(0.3, chain.steps[1].volume)
        self.assertEqual(0.3, chain.steps[2].volume)

    def test__process_happy_path(self):
        # 1. Arrange
        bus = Mock()
        om = OrderManager(bus, {}, Mock())
        steps = [
            AChainStep("BTCUSDT", OrderSide.SELL, 0.01, 0.1),
            AChainStep("USDTETH", OrderSide.SELL, 0.01, 0.1),
            AChainStep("BTCETH", OrderSide.BUY, 0.01, 0.1),
        ]
        chain = AChain("BTC", steps, 0.01, 10, ORDER_PROFIT_THRESHOLD_USD + 1)
        # 2. Act
        om._process(chain)
        # 3. Assert
        # todo Check how bus has been called
        # bus.assert_called()
