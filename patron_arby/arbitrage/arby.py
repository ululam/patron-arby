import logging
from typing import Callable, Dict, List, Tuple

from patron_arby.arbitrage.arby_utils import ArbyUtils
from patron_arby.arbitrage.market_data import COINS_PATH_SEPARATOR, MarketData
from patron_arby.common.chain import AChain, AChainStep, OrderSide
from patron_arby.common.util import current_time_ms

log = logging.getLogger(__name__)


class PetroniusArbiter:
    """
    Responsible for find triangle arbitrage in market data
    """

    def __init__(self, market_data: MarketData, trade_fees: Dict, default_trade_fee: float = 0.001) -> None:
        super().__init__()
        self.market_data = market_data
        self.previous_run_time = 0
        self.fees = trade_fees
        self.default_fee = default_trade_fee

    # @measure_execution_time
    def find(self, on_positive_arbitrage_found_callback: Callable[[AChain], None] = None) -> List[AChain]:
        log.fine(" =========== Starting find cycle")
        price_volume_data = self.market_data.get()
        if len(price_volume_data) == 0:
            log.info("No data present yet, skipping finding arbitrage")
            return list()

        result = list()
        for coins_path, markets_path in self.market_data.paths_3.items():
            coins = coins_path.split(COINS_PATH_SEPARATOR)
            markets = markets_path.split(COINS_PATH_SEPARATOR)

            valid_3_chain = True
            steps: List[AChainStep] = list()
            for i in range(0, len(markets)):
                bidask_dict = price_volume_data.get(markets[i])
                if not bidask_dict:  # or bidask_dict.get("LastUpdateTimeMs") < self.previous_run_time:
                    valid_3_chain = False
                    break
                step = self._get_coin_price_and_quantity_in_another_coin(bidask_dict, coins[i + 1])
                steps.append(step)

            if not valid_3_chain:
                continue

            # roi, profit = self._calc_roi_and_profit(coin_xy_price_quantity)
            steps, roi, profit = self._calc_and_set_roi_profit_and_max_volume(steps)
            profit_usd = self._get_profit_in_usd(coins[0], profit)

            # Update volumes according to max available volume

            chain = AChain(initial_coin=coins[0], steps=steps, roi=roi, profit=profit, profit_usd=profit_usd)

            if profit > 0:
                log.debug(f"Found positive arbitrage chain: {chain}")
                if on_positive_arbitrage_found_callback:
                    on_positive_arbitrage_found_callback(chain)

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

    def _get_coin_price_and_quantity_in_another_coin(self, bidask_dict: Dict, coin: str) -> AChainStep:
        """
        :param bidask_dict:
        :param coin:
        :return: [price, volume, True if BUY, False if SELL]
        """
        market = bidask_dict.get("Market")

        base_quote = market.split("/")
        if coin == base_quote[0]:
            forward_buy = True      # We buy our coin using other coin as base
        elif coin == base_quote[1]:
            forward_buy = False     # Our coin is baee, we should reverse price
        else:
            raise AttributeError(f"Coin '{coin}' is not traded within market '{market}'")

        trade_fee = self._get_trade_fee(market.replace("/", ""))

        if forward_buy:
            ask = bidask_dict.get("BestAsk")    # bid < ask
            ask_quantity = bidask_dict.get("BestAskQuantity")
            return AChainStep(market, OrderSide.BUY, price=ask * (1 + trade_fee),
                volume=ask_quantity)

        bid = bidask_dict.get("BestBid")
        bid_quantity = bidask_dict.get("BestBidQuantity")
        price = bid * (1 - trade_fee)
        # todo Fix for SELL
        quantity = bid_quantity * price
        # quantity = bid_quantity / price

        return AChainStep(market, OrderSide.SELL, price=price, volume=quantity)

    def _get_profit_in_usd(self, coin: str, volume: float):
        if "USD" in coin:
            return volume
        coin_price_in_usd = self.market_data.get_coin_price_in_usd(coin)
        if not coin_price_in_usd:
            log.fine(f"USD price for coin '{coin}' not found")
            return -1
        return volume * coin_price_in_usd

    def _print_buy_info(self, coin_1: str, coin_2: str, coin_21_price: float, coin_21_quantity: float):
        if log.isEnabledFor(logging.FINE):
            log.fine(f"We can buy {coin_21_quantity} {coin_2}s for {coin_1} at the price {coin_21_price}")
            log.fine(f"  That means, we are spending {coin_21_quantity*coin_21_price} {coin_1} for {coin_21_quantity}"
                  f" {coin_2}s")

    def _out_path(self, out_dict: Dict):
        coin_b = out_dict.get("coin_b")
        coin_c = out_dict.get("coin_c")
        coin_a = out_dict.get("coin_a")

        sentence = f"\t We {self._get_subsentence(coin_b, coin_a.get('Coin'))}.\n"
        sentence += f"\t Then, we {self._get_subsentence(coin_c, coin_b.get('Coin'))}.\n"
        sentence += f"\t Last, we {self._get_subsentence(coin_a, coin_c.get('Coin'))}.\n"
        log.debug(sentence)

    def _get_subsentence(self, coin_dict: Dict, next_coin: str) -> str:
        return f"{coin_dict.get('Buy/Sell')} {coin_dict.get('Quantity')} {coin_dict.get('Coin')} for 1 {next_coin}" \
               f" at the price {coin_dict.get('Price')} via {coin_dict.get('Market')}"
