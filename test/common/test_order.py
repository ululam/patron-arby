import time
from unittest import TestCase

from patron_arby.common.order import Order, OrderSide


class TestOrder(TestCase):
    def test__to_from_dict(self):
        # 1. Arrange
        o = Order("asd", OrderSide.SELL, "BTCETH", price=0.01, quantity=0.2)
        o.original_order = {"original": {"a": 1}}
        o.arbitrage_id = "Arb_id"
        # 2. Act
        order_dict = o.to_dict()
        print(order_dict)
        o2 = Order.from_dict(order_dict)
        print(o2)
        # 3. Assert
        self.assertEqual(o, o2)
        self.assertEqual(o.arbitrage_id, o2.arbitrage_id)

    def test__two_orders_have_different_createdat(self):
        # 1. Arrange
        o1 = Order("asd", OrderSide.SELL, "BTCETH", price=0.01, quantity=0.2)
        time.sleep(0.01)
        o2 = Order("asd", OrderSide.SELL, "BTCETH", price=0.01, quantity=0.2)
        self.assertNotEqual(o1.created_at, o2.created_at)
