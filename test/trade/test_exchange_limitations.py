from decimal import Decimal
from unittest import TestCase

from patron_arby.common.order import Order, OrderSide
from patron_arby.exchange.binance.limitations import BinanceExchangeLimitations


class TestBinanceExchangeLimitations(TestCase):
    def test__adjust_price_and_volume_to_market_requirements(self):
        # 1. Arrange
        exchange_info = {
            "symbols": [{
                "symbol": "BTCUSD",
                "filters": [
                    {"filterType": "PRICE_FILTER", "tickSize": 0.0100},
                    {"filterType": "LOT_SIZE", "stepSize": 0.001}
                ]
            }]
        }
        limits = BinanceExchangeLimitations(exchange_info)
        order = Order("", OrderSide.SELL, "BTCUSD", price=12.34245435, quantity=44.345945345345)
        # 2. Act
        order = limits.adjust_price_and_volume_to_market_requirements(order)
        # 3. Assert
        self.assertEqual(Decimal("12.34"), order.price)
        self.assertEqual(Decimal("44.346"), order.quantity)
