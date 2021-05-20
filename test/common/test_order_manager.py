from decimal import Decimal
from unittest import TestCase
from unittest.mock import Mock

from patron_arby.common.chain import AChain, AChainStep
from patron_arby.common.exchange_limitation import ExchangeLimitation
from patron_arby.common.order import Order, OrderSide
from patron_arby.config.base import ORDER_PROFIT_THRESHOLD_USD
from patron_arby.order.manager import OrderManager


class TestOrderManager(TestCase):
    def test___align_price_and_volume_to_market_requirements(self):
        # 1. Arrange
        limits = {"BTCUSD": {
            ExchangeLimitation.MIN_PRICE_STEP: "0.01",
            ExchangeLimitation.MIN_VOLUME_STEP: "0.001"
        }}
        om = OrderManager(Mock(), limits, Mock())
        order = Order("", OrderSide.SELL, "BTCUSD", 12.34245435, 44.345945345345)
        # 2. Act
        order = om._align_price_and_volume_to_market_requirements(order)
        # 3. Assert
        self.assertEqual(Decimal("12.34"), order.price)
        self.assertEqual(Decimal("44.346"), order.quantity)

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
