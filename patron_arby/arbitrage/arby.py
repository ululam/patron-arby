import logging
from typing import Dict, List, Tuple

from patron_arby.arbitrage.market_data import COINS_PATH_SEPARATOR, MarketData
from patron_arby.common.decorators import log_execution_time
from patron_arby.common.util import current_time_ms

log = logging.getLogger(__name__)


class PetroniusArbiter:
    """
    Responsible for find triangle arbitrage in market data
    """

    def __init__(self, market_data: MarketData, default_order_fee_factor: float = 0.01) -> None:
        super().__init__()
        self.market_data = market_data
        self.default_order_fee_factor = default_order_fee_factor
        self.previous_run_time = 0

    @log_execution_time
    def find(self) -> List[Dict]:
        log.debug(" =========== Starting find cycle")
        price_volume_data = self.market_data.get()
        if len(price_volume_data) == 0:
            log.warning("No data present yet, skipping finding arbitrage")
            return list()

        result = list()
        for coins_path, markets_path in self.market_data.paths_3.items():
            coins = coins_path.split(COINS_PATH_SEPARATOR)
            markets = markets_path.split(COINS_PATH_SEPARATOR)

            bidask_ba_dict = price_volume_data.get(markets[0])
            if not bidask_ba_dict:  # or bidask_ba_dict.get("LastUpdateTimeMs") < self.previous_run_time:
                continue
            bidask_cb_dict = price_volume_data.get(markets[1])
            if not bidask_cb_dict:  # or bidask_cb_dict.get("LastUpdateTimeMs") < self.previous_run_time:
                continue
            bidask_ac_dict = price_volume_data.get(markets[2])
            if not bidask_ac_dict:  # or bidask_ac_dict.get("LastUpdateTimeMs") < self.previous_run_time:
                continue

            coin_ba_price, coin_ba_quantity = \
                self._get_coin_price_and_quantity_in_another_coin(bidask_ba_dict, coins[1])
            if not coin_ba_price:
                continue
            coin_cb_price, coin_cb_quantity = \
                self._get_coin_price_and_quantity_in_another_coin(bidask_cb_dict, coins[2])
            if not coin_cb_price:
                continue
            coin_ac_price, coin_ac_quantity = \
                self._get_coin_price_and_quantity_in_another_coin(bidask_ac_dict, coins[3])
            if not coin_ac_price:
                continue

            max_coin_a_volume_available = self._calculate_max_available_triangle_volume(
                (coin_ba_price, coin_ba_quantity),
                (coin_cb_price, coin_cb_quantity),
                (coin_ac_price, coin_ac_quantity)
            )

            roi = self._calculate_triangle_roi(coin_ba_price, coin_cb_price, coin_ac_price)
            profit = max_coin_a_volume_available * roi

            result.append({
                "coin_path": coins_path,
                "market_path": markets_path,
                "roi": roi,
                "profit": profit
            })

        self.previous_run_time = current_time_ms()
        log.debug(" =========== End find cycle")
        return result

    @log_execution_time
    def find3(self) -> List[Dict]:
        log.debug(" =========== Starting find cycle")
        price_volume_data = self.market_data.get()
        if len(price_volume_data) == 0:
            log.warning("No data present yet, skipping finding arbitrage")
            return list()

        result = list()
        for coins_path, markets_path in self.market_data.paths_3.items():
            coins = coins_path.split(COINS_PATH_SEPARATOR)
            markets = markets_path.split(COINS_PATH_SEPARATOR)

            coin_xy_price_quantity = list()
            valid_3_chain = True
            for i in range(0, len(markets)):
                bidask_dict = price_volume_data.get(markets[i])
                if not bidask_dict:  # or bidask_dict.get("LastUpdateTimeMs") < self.previous_run_time:
                    valid_3_chain = False
                    break
                coin_xy_price, coin_xy_quantity = \
                    self._get_coin_price_and_quantity_in_another_coin(bidask_dict, coins[i + 1])
                if not coin_xy_price:
                    valid_3_chain = False
                    break
                coin_xy_price_quantity.append((coin_xy_price, coin_xy_quantity))

            if not valid_3_chain:
                continue

            max_coin_a_volume_available = self._calculate_max_available_triangle_volume(
                coin_xy_price_quantity[0], coin_xy_price_quantity[1], coin_xy_price_quantity[2]
            )

            roi = self._calculate_triangle_roi(
                coin_xy_price_quantity[0][0], coin_xy_price_quantity[1][0], coin_xy_price_quantity[2][0]
            )
            profit = max_coin_a_volume_available * roi

            result.append({
                "coin_path": coins_path,
                "market_path": markets_path,
                "roi": roi,
                "profit": profit
            })

        self.previous_run_time = current_time_ms()
        log.debug(" =========== End find cycle")
        return result

    @staticmethod
    def _calculate_max_available_triangle_volume(coin_ba_price_volume: Tuple[float, float],
                                                 coin_cb_price_volume: Tuple[float, float],
                                                 coin_ac_price_volume: Tuple[float, float]) -> float:
        """
        :param coin_ba_price_volume: [price, volume_available] for coin_b in coin_a units
        :param coin_cb_price_volume: [price, volume_available] for coin_c in coin_b units
        :param coin_ac_price_volume: [price, volume_available] for coin_a in coin_c units
        :return: Maximum available volume of coin_a we can trade in the given chain [a -> b -> c -> a]
        """
        # Bring all the volumes to the same unit
        coin_ba_in_a_volume = coin_ba_price_volume[0] * coin_ba_price_volume[1]
        coin_cb_in_a_volume = coin_cb_price_volume[0] * coin_cb_price_volume[1] * coin_ba_price_volume[0]
        coin_ac_in_a_volume = coin_ac_price_volume[1]
        return min(coin_ba_in_a_volume, coin_cb_in_a_volume, coin_ac_in_a_volume)

    @staticmethod
    def _calculate_triangle_roi(*prices):
        factor = 1
        for p in prices:
            factor = factor * p
        return 1 - factor

    def _get_coin_price_and_quantity_in_another_coin(self, bidask_dict: Dict, coin: str) \
            -> Tuple[float, float]:
        market = bidask_dict.get("Market")

        base_quote = market.split("/")
        if coin == base_quote[0]:
            forward_buy = True      # We buy our coin using other coin as base
        elif coin == base_quote[1]:
            forward_buy = False     # Our coin is baee, we should reverse price
        else:
            raise AttributeError(f"Coin '{coin}' is not traded within market '{market}'")

        if forward_buy:
            ask = bidask_dict.get("BestAsk")    # bid < ask
            ask_quantity = bidask_dict.get("BestAskQuantity")
            return ask * (1 + self.default_order_fee_factor), ask_quantity

        bid = bidask_dict.get("BestBid")
        bid_quantity = bidask_dict.get("BestBidQuantity")
        price = 1 / (bid * (1 - self.default_order_fee_factor))
        quantity = bid_quantity / price

        return price, quantity

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
