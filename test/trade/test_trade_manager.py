from decimal import Decimal
from unittest import TestCase
from unittest.mock import Mock, call, patch

from patron_arby.common.chain import AChain, AChainStep
from patron_arby.common.exchange_limitation import ExchangeLimitation
from patron_arby.common.order import Order, OrderSide
from patron_arby.config.base import ORDER_PROFIT_THRESHOLD_USD
from patron_arby.exchange.registry import BalancesRegistry
from patron_arby.trade.manager import TradeManager


class TestTradeManager(TestCase):
    def test__round_price_and_volume_to_market_requirements(self):
        # 1. Arrange
        limits = {"BTCUSD": {
            ExchangeLimitation.MIN_PRICE_STEP: 0.01,
            ExchangeLimitation.MIN_VOLUME_STEP: 0.001
        }}
        tm = TradeManager(Mock(), limits, Mock())
        order = Order("", OrderSide.SELL, "BTCUSD", price=12.34245435, quantity=44.345945345345)
        # 2. Act
        order = tm._round_price_and_volume_to_market_requirements(order)
        # 3. Assert
        self.assertEqual(Decimal("12.34"), order.price)
        self.assertEqual(Decimal("44.346"), order.quantity)

    def test__shrink_volumes_according_to_balances__simple_case(self):
        # 1. Arrange
        balances = BalancesRegistry({"BTC": 20, "USDT": 500, "ETH": 10})
        tm = TradeManager(Mock(), {}, balances_registry=balances)
        chain = AChain("BTC", [
            AChainStep("BTC/USDT", OrderSide.BUY, 30_000, 0.01),
            AChainStep("ETH/BTC", OrderSide.BUY, 0.05, 5),
            AChainStep("ETH/USDT", OrderSide.SELL, 2500, 5)
        ])
        # 2. Act
        chain = tm._shrink_volumes_according_to_balances(chain, 0.3)
        # 3. Assert
        self.assertEqual(0.005, chain.steps[0].volume)
        self.assertEqual(2.5, chain.steps[1].volume)
        self.assertEqual(2.5, chain.steps[2].volume)

    def test__shrink_volumes_according_to_balances__no_shrink_required(self):
        # 1. Arrange
        balances = BalancesRegistry({"BTC": 200, "USDT": 50000, "ETH": 10000})
        tm = TradeManager(Mock(), {}, balances_registry=balances)
        chain = AChain("BTC", [
            AChainStep("BTC/USDT", OrderSide.BUY, 30_000, 0.01),
            AChainStep("ETH/BTC", OrderSide.BUY, 0.05, 5),
            AChainStep("ETH/USDT", OrderSide.SELL, 2500, 5)
        ])
        # 2. Act
        chain = tm._shrink_volumes_according_to_balances(chain, 0.3)
        # 3. Assert
        self.assertEqual(0.01, chain.steps[0].volume)
        self.assertEqual(5, chain.steps[1].volume)
        self.assertEqual(5, chain.steps[2].volume)

    def test__shrink_volumes_according_to_balances__all_balances_unsufficient(self):
        # 1. Arrange
        balances = BalancesRegistry({"BTC": 0.1, "USDT": 300, "ETH": 1})
        tm = TradeManager(Mock(), {}, balances_registry=balances)

        chain = AChain("BTC", [
            AChainStep("BTC/USDT", OrderSide.BUY, 30_000, 0.01),
            AChainStep("ETH/BTC", OrderSide.BUY, 0.05, 5),
            AChainStep("ETH/USDT", OrderSide.SELL, 2500, 5)     # <- Max volume/balance factor
        ])
        # 2. Act
        chain = tm._shrink_volumes_according_to_balances(chain, 0.3)
        # 3. Assert
        self.assertEqual(0.0006, chain.steps[0].volume)
        self.assertEqual(0.3, chain.steps[1].volume)
        self.assertEqual(0.3, chain.steps[2].volume)

    def test__process_happy_path(self):
        # 1. Arrange
        bus = Mock()
        tm = TradeManager(bus, {}, Mock())
        steps = [
            AChainStep("BTCUSDT", OrderSide.SELL, 0.01, 0.1),
            AChainStep("USDTETH", OrderSide.SELL, 0.01, 0.1),
            AChainStep("BTCETH", OrderSide.BUY, 0.01, 0.1),
        ]
        chain = AChain("BTC", steps, 0.01, 10, ORDER_PROFIT_THRESHOLD_USD + 1)
        # 2. Act
        tm._process_chain(chain)
        # 3. Assert
        # todo Check how bus has been called
        # bus.assert_called()

    def test__stop_trading(self):
        # 1. Arrange
        bus = Mock()
        bus.is_stop_trading = Mock(return_value=True)
        bus.store_positive_arbitrages_queue.put = Mock()
        tm = TradeManager(bus, {}, Mock())
        with patch.object(tm, "_on_arbitrage_option_found", wraps=tm._on_arbitrage_option_found) as _on_found_method:
            chain = AChain("BTC", [], 0.01, 10, ORDER_PROFIT_THRESHOLD_USD + 1)
            # 2. Act
            tm._process_chain_set(chains={chain})
            # 3. Assert
            self.assertEqual("Stop trading flag is True, ignoring arbitrage chain", chain.comment)
            _on_found_method.assert_not_called()
            bus.store_positive_arbitrages_queue.put.assert_called_once_with(chain)

    def test__trading_goes_on_if_stop_flag_is_false(self):
        # 1. Arrange
        bus = Mock()
        bus.is_stop_trading = Mock(return_value=False)
        bus.store_positive_arbitrages_queue = Mock()
        bus.store_positive_arbitrages_queue.put = Mock()
        tm = TradeManager(bus, {}, Mock())
        with patch.object(tm, "_on_arbitrage_option_found", wraps=tm._on_arbitrage_option_found) as _on_found_method:
            chain = AChain("BTC", [], 0.01, 10, ORDER_PROFIT_THRESHOLD_USD + 1)
            # 2. Act
            tm._process_chain_set(chains={chain})
            # 3. Assert
            _on_found_method.assert_called_with(chain)
            bus.store_positive_arbitrages_queue.put.assert_called_once_with(chain)

    def test__sort_chains_by_profitability_roi(self):
        # 1. Arrange
        tm = TradeManager(Mock(), {}, Mock(), fire_only_top_arbitrage=True, sort_arbitrage_by_roi=True)
        chain1 = AChain(roi=0.1, profit=10)
        chain2 = AChain(roi=0.2, profit=5)
        chains = {chain1, chain2}
        # 2. Act
        chain_list = tm._sort_chains_by_profitability(chains)
        # 3. Assert
        self.assertEqual(2, len(chain_list))
        self.assertEqual(chain2, chain_list[0])
        self.assertEqual(chain1, chain_list[1])

    def test__sort_chains_by_profitability_profit(self):
        # 1. Arrange
        tm = TradeManager(Mock(), {}, Mock(), fire_only_top_arbitrage=True, sort_arbitrage_by_roi=False)
        chain1 = AChain(roi=0.1, profit=10)
        chain2 = AChain(roi=0.2, profit=5)
        chains = {chain1, chain2}
        # 2. Act
        chain_list = tm._sort_chains_by_profitability(chains)
        # 3. Assert
        self.assertEqual(2, len(chain_list))
        self.assertEqual(chain1, chain_list[0])
        self.assertEqual(chain2, chain_list[1])

    def test__process_chain_set__fire_only_top_arbitrage(self):
        # 1. Arrange
        bus = Mock()
        bus.store_positive_arbitrages_queue = Mock()
        bus.store_positive_arbitrages_queue.put = Mock()
        tm = TradeManager(bus, {}, Mock(), fire_only_top_arbitrage=True)
        tm._process_chain = Mock(return_value="Mock_Processed")
        chain1 = AChain(roi=0.1, profit=1)
        chain2 = AChain(roi=0.2, profit=2)
        chains = {chain1, chain2}
        # 2. Act
        tm._process_chain_set(chains)
        # 3. Assert
        tm._process_chain.assert_called_once_with(chain2)
        self.assertTrue(chain1.comment.startswith("Processing only the top chain"), chain1.comment)
        # All chains put to "store" queue regardless of whether have been processed or not
        self.assertEqual([call(chain2), call(chain1)], bus.store_positive_arbitrages_queue.put.mock_calls)

    def test__process_chain_set__fire_all_arbitrages(self):
        # 1. Arrange
        bus = Mock()
        bus.store_positive_arbitrages_queue.put = Mock()
        tm = TradeManager(bus, {}, Mock(), fire_only_top_arbitrage=False)
        tm._process_chain = Mock(return_value="Mock_Processed")
        chain1 = AChain(roi=0.1, profit=1)
        chain2 = AChain(roi=0.2, profit=2)
        chains = {chain1, chain2}
        # 2. Act
        tm._process_chain_set(chains)
        # 3. Assert
        self.assertEqual([call(chain2), call(chain1)], tm._process_chain.mock_calls)
        # All chains put to "store" queue regardless of whether have been processed or not
        self.assertEqual([call(chain2), call(chain1)], bus.store_positive_arbitrages_queue.put.mock_calls)
