from unittest import TestCase
from unittest.mock import Mock

from patron_arby.common.bus import Bus
from patron_arby.exchange.binance.balance_checker import BalancesChecker


class TestBalancesChecker(TestCase):
    def test__breaching_threshold_stops_trading(self):
        # 1. Arrange
        threshold = 100
        bus = Bus()
        registry = Mock()
        registry.get_balance.return_value = 1
        registry.get_balance_usd.return_value = 1
        coins_of_interest = {"BTC", "ETH"}
        balances_checker = BalancesChecker(bus, registry, coins_of_interest, threshold)
        # 2. Act
        balances_checker.check_balance()
        # 3. Assert
        self.assertTrue(bus.is_stop_trading)

    def test__not_breaching_threshold_does_not_stop_trading(self):
        # 1. Arrange
        threshold = 100
        bus = Bus()
        registry = Mock()
        registry.get_balance.return_value = 1
        registry.get_balance_usd.return_value = threshold
        coins_of_interest = {"BTC", "ETH"}
        balances_checker = BalancesChecker(bus, registry, coins_of_interest, threshold)
        # 2. Act
        balances_checker.check_balance()
        # 3. Assert
        self.assertFalse(bus.is_stop_trading)
