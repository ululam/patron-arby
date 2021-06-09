from unittest import TestCase
from unittest.mock import Mock

from patron_arby.common.bus import Bus
from patron_arby.exchange.binance.balances_checker import BalancesChecker
from patron_arby.exchange.registry import Balance


class TestBalancesChecker(TestCase):
    def test__breaching_threshold_stops_trading(self):
        # 1. Arrange
        threshold = 100
        bus = Bus()
        registry = Mock()
        registry.get_balances.return_value = {"BTC": Balance(1, threshold - 1)}
        registry.is_empty.return_value = False
        coins_of_interest = {"BTC", "ETH"}
        balances_checker = BalancesChecker(bus, registry, coins_of_interest, threshold)
        # Disable method call
        balances_checker.log_balances = Mock()
        # 2. Act
        balances_checker.check_balance()
        # 3. Assert
        self.assertTrue(bus.is_stop_trading())

    def test__not_breaching_threshold_does_not_stop_trading(self):
        # 1. Arrange
        threshold = 100
        bus = Bus()
        registry = Mock()
        registry.get_balances.return_value = {"BTC": Balance(1, threshold), "ETH": Balance(1, 1)}
        registry.is_empty.return_value = False
        coins_of_interest = {"BTC", "ETH"}
        balances_checker = BalancesChecker(bus, registry, coins_of_interest, threshold)
        # Disable method call
        balances_checker.log_balances = Mock()
        # 2. Act
        balances_checker.check_balance()
        # 3. Assert
        self.assertFalse(bus.is_stop_trading())
