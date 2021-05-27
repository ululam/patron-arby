import logging
from typing import Callable, Dict, List, Set, Tuple

from patron_arby.arbitrage.arby_utils import ArbyUtils
from patron_arby.arbitrage.market_data import COINS_PATH_SEPARATOR, MarketData
from patron_arby.common.chain import AChain, AChainStep, OrderSide
from patron_arby.common.ticker import Ticker
from patron_arby.common.util import current_time_ms

log = logging.getLogger(__name__)


class PetroniusArbiter:
    """
    Responsible for find triangle arbitrage in market data
    """

    def __init__(self, market_data: MarketData, trade_fees: Dict,
                 on_positive_arbitrage_found_callback: Callable[[AChain], None] = None,
                 default_trade_fee: float = 0.001) -> None:
        super().__init__()
        self.market_data = market_data
        self.previous_run_time = 0
        self.fees = trade_fees
        self.default_fee = default_trade_fee
        self.on_positive_arbitrage_found_callback = on_positive_arbitrage_found_callback

    # @measure_execution_time
    def find(self, updated_markets: Set) -> List[AChain]:
        # todo Lookup only chains coming via the given updated_markets
        log.fine(" =========== Starting find cycle")
        price_volume_data = self.market_data.get()
        if len(price_volume_data) == 0:
            log.info("No data present yet, skipping finding arbitrage")
            return list()

        result = list()

        # for coins_path, markets_path in self.market_data.paths_3.items():
        for coins_path, markets_path in self.market_data.filter_path3_by_markets(updated_markets):
            coins = coins_path.split(COINS_PATH_SEPARATOR)
            markets = markets_path.split(COINS_PATH_SEPARATOR)

            valid_3_chain = True
            steps: List[AChainStep] = list()
            for i in range(0, len(markets)):
                ticker = price_volume_data.get(markets[i])
                if not ticker:  # or bidask_dict.get("LastUpdateTimeMs") < self.previous_run_time:
                    valid_3_chain = False
                    break
                step = self._create_chain_step(ticker, coins[i + 1])
                steps.append(step)

            if not valid_3_chain:
                continue

            # roi, profit = self._calc_roi_and_profit(coin_xy_price_quantity)
            steps, roi, profit = self._calc_and_set_roi_profit_and_max_volume(steps)
            profit_usd = self._get_profit_in_usd(coins[0], profit)

            # Update volumes according to max available volume

            chain = AChain(initial_coin=steps[0].spending_coin(), steps=steps, roi=roi, profit=profit,
                profit_usd=profit_usd)

            if profit > 0:
                log.debug(f"Found positive arbitrage chain: {chain}")
                if self.on_positive_arbitrage_found_callback:
                    self.on_positive_arbitrage_found_callback(chain)

            result.append(chain)

        self.previous_run_time = current_time_ms()
        log.fine(" =========== End find cycle")

        return result

    def update_commissions(self, commissions: Dict):
        self.fees = commissions

    def _calc_and_set_roi_profit_and_max_volume(self, steps: List[AChainStep]) -> Tuple[List[AChainStep], float, float]:
        roi = self._calculate_triangle_roi(steps[0], steps[1], steps[2])

        step1, step2, step3 = ArbyUtils.calc_and_return_max_available_triangle_volume(steps[0], steps[1], steps[2])

        profit = step1.volume * roi

        return [step1, step2, step3], roi, profit

    def _get_trade_fee(self, market: str) -> float:
        return self.fees.get(market, self.default_fee)

    @staticmethod
    def _calculate_triangle_roi(*steps):
        factor = 1
        for step in steps:
            factor = factor * (step.price if step.is_buy() else 1 / step.price)
        return 1 - factor

    def _create_chain_step(self, ticker: Ticker, coin: str) -> AChainStep:
        """
        :param bidask_dict: Ticker
        :param coin:
        :return: [price, volume, True if BUY, False if SELL]
        """
        base_quote = ticker.market.split("/")
        if coin == base_quote[0]:
            forward_buy = True      # We buy our coin using other coin as base
        elif coin == base_quote[1]:
            forward_buy = False     # Our coin is base, we are "selling"
        else:
            raise AttributeError(f"Coin '{coin}' is not traded within market '{ticker.market}'")

        trade_fee = self._get_trade_fee(ticker.market.replace("/", ""))

        if forward_buy:
            ask = ticker.best_ask    # bid < ask
            ask_quantity = ticker.best_ask_quantity
            return AChainStep(ticker.market, OrderSide.BUY, price=ask * (1 + trade_fee), volume=ask_quantity)

        bid = ticker.best_bid
        bid_quantity = ticker.best_bid_quantity
        price = bid * (1 - trade_fee)
        quantity = bid_quantity * price

        return AChainStep(ticker.market, OrderSide.SELL, price=price, volume=quantity)

    def _get_profit_in_usd(self, coin: str, volume: float):
        if "USD" in coin:
            return volume
        coin_price_in_usd = self.market_data.get_coin_price_in_usd(coin)
        if not coin_price_in_usd:
            log.fine(f"USD price for coin '{coin}' not found")
            return -1
        return volume * coin_price_in_usd
