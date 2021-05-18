from unittest import TestCase

from patron_arby.common.order import Order, OrderSide


class TestOrder(TestCase):
    def test__to_dict(self):
        # 1. Arrange
        o = Order("asd", OrderSide.SELL, "BTCETH", 0.01, 0.2)
        o.original_order = {"original": {"a": 1}}
        o.arbitrage_id = "Arb_id"
        o.status = "SOME STATUS"
        # 2. Act
        order_dict = o.to_dict()
        o2 = Order.from_dict(order_dict)
        # 3. Assert
        self.assertEqual(o, o2)
