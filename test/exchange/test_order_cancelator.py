from unittest import TestCase
from unittest.mock import Mock, call

from patron_arby.common.order import Order, OrderSide
from patron_arby.common.util import current_time_ms
from patron_arby.exchange.order_cancelator import OrderCancelator


class TestOrderCancelator(TestCase):
    def test__one_out_of_2_should_be_cancelled(self):
        # 1. Arrange
        exchange_api = Mock()
        order_ttl_ms = 10
        order1 = Order(client_order_id="1_order_1", order_side=OrderSide.BUY, symbol="BTCUSDT", quantity=0.1,
            price=30_000, created_at=current_time_ms() + 2000, order_id="123")
        order2 = Order(client_order_id="1_order_2", order_side=OrderSide.BUY, symbol="ETHUSDT", quantity=0.1,
            price=2500, created_at=current_time_ms() - 2 * order_ttl_ms, order_id="456")
        exchange_api.get_open_orders.return_value = [order1, order2]
        oc = OrderCancelator(exchange_api, order_ttl_ms)
        # 2. Act
        oc._do_run()
        # 3. Assert
        exchange_api.cancel_order.assert_called_once_with(symbol=order2.symbol, order_id=order2.order_id)

    def test__two_orders_to_cancel(self):
        # 1. Arrange
        exchange_api = Mock()
        order_ttl_ms = 10
        order1 = Order(client_order_id="1_order_1", order_side=OrderSide.BUY, symbol="BTCUSDT", quantity=0.1,
            price=30_000, created_at=0, order_id="123")
        order2 = Order(client_order_id="1_order_2", order_side=OrderSide.BUY, symbol="ETHUSDT", quantity=0.1,
            price=2500, created_at=0, order_id="456")
        exchange_api.get_open_orders.return_value = [order1, order2]
        oc = OrderCancelator(exchange_api, order_ttl_ms)
        # 2. Act
        oc._do_run()
        # 3. Assert
        self.assertEqual([call(symbol=order1.symbol, order_id=order1.order_id),
                          call(symbol=order2.symbol, order_id=order2.order_id)], exchange_api.cancel_order.mock_calls)

    def test__only_our_orders_cancelled(self):
        # 1. Arrange
        exchange_api = Mock()
        order_ttl_ms = 10
        order1 = Order(client_order_id="1_order_1", order_side=OrderSide.BUY, symbol="BTCUSDT", quantity=0.1,
            price=30_000, created_at=0, order_id="123")     # our client_order_id
        order2 = Order(client_order_id="not_our_order", order_side=OrderSide.BUY, symbol="ETHUSDT", quantity=0.1,
            price=2500, created_at=0, order_id="456")     # not our client_order_id
        exchange_api.get_open_orders.return_value = [order1, order2]
        oc = OrderCancelator(exchange_api, order_ttl_ms)
        # 2. Act
        oc._do_run()
        # 3. Assert
        exchange_api.cancel_order.assert_called_once_with(symbol=order1.symbol, order_id=order1.order_id)
