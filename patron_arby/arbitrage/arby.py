import logging
from typing import Dict, List, Tuple

from patron_arby.arbitrage.market_data import MarketData
from patron_arby.common.decorators import log_execution_time

log = logging.getLogger(__name__)


class PetroniusArbiter:
    """
    Responsible for find triangle arbitrage in market data
    """

    def __init__(self, market_data: MarketData) -> None:
        super().__init__()
        self.market_data = market_data

    @log_execution_time
    def find(self) -> List[Dict]:
        log.info(" =========== Starting find cycle")
        data = self.market_data.get()
        if len(data) == 0:
            log.warning("No data present yet, skipping finding arbitrage")
            return list()

        market_paths = self.market_data.get_market_paths()
        result = list()
        # todo Optimize: don't calculate if no new tickers arrived (remember last update time for ticker in market_data)
        for coin_a, coin_ba_paths in market_paths.items():
            for coin_b_market in coin_ba_paths:
                if coin_b_market not in data:
                    # No ticker arrived yet
                    continue
                coin_ba_price, coin_ba_quantity, coin_b = self._get_coin_data(coin_b_market, coin_a, data)
                self._print_buy_info(coin_a, coin_b, coin_ba_price, coin_ba_quantity)

                coin_bc_paths = market_paths.get(coin_b)
                if not coin_bc_paths:
                    # No further paths
                    continue
                for coin_c_market in coin_bc_paths:
                    if coin_c_market == coin_b_market:
                        # Avoid circular paths with depth 1
                        continue
                    if coin_c_market not in data:
                        # No ticker arrived yet
                        continue

                    coin_cb_price, coin_cb_quantity, coin_c = self._get_coin_data(coin_c_market, coin_b, data)
                    self._print_buy_info(coin_b, coin_c, coin_cb_price, coin_cb_quantity)

                    # Return to coin A
                    coin_a_market_fwd = f"{coin_c}/{coin_a}"
                    coin_a_market_reverse = f"{coin_a}/{coin_c}"
                    if coin_a_market_fwd == coin_c_market or coin_a_market_reverse == coin_c_market:
                        continue
                    if coin_a_market_fwd in data.keys():
                        coin_a_market = coin_a_market_fwd
                    elif coin_a_market_reverse in data.keys():
                        coin_a_market = coin_a_market_reverse
                    else:
                        # Path not present
                        continue

                    coin_ac_price, coin_ac_quantity = \
                        self._get_coin_price_and_quantity_in_another_coin(data.get(coin_a_market), coin_a)
                    self._print_buy_info(coin_c, coin_a, coin_ac_price, coin_ac_quantity)

                    max_coin_a_volume_available = self._calculate_max_available_triangle_volume(
                        (coin_ba_price, coin_ba_quantity),
                        (coin_cb_price, coin_cb_quantity),
                        (coin_ac_price, coin_ac_quantity)
                    )

                    roi = self._calculate_triangle_roi(coin_ba_price, coin_cb_price, coin_ac_price)

                    profit = max_coin_a_volume_available * roi

                    result.append({
                        "path": self._path(coin_a, coin_b, coin_c, coin_a),
                        "roi": roi,
                        "profit": profit
                    })

                    log.debug(f">>> We can run through {max_coin_a_volume_available} {coin_a}s with {roi} ROI, "
                              f"resulting in {profit} {coin_a}s profit")
                    log.debug(f"{self._path(coin_a, coin_b, coin_c, coin_a)}: = {profit}\n")

        log.info(" =========== End find cycle")
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
        log.debug(f"Volumes available in coin_a units: {coin_ba_in_a_volume}, {coin_cb_in_a_volume},"
                  f" {coin_ac_in_a_volume}")
        return min(coin_ba_in_a_volume, coin_cb_in_a_volume, coin_ac_in_a_volume)

    @staticmethod
    def _calculate_triangle_roi(*prices):
        factor = 1
        for p in prices:
            factor = factor * p
        return 1 - factor

    def _get_coin_data(self, coin_market: str, previous_coin: str, market_data: Dict) -> Tuple[float, float, str]:
        base_quote = coin_market.split("/")
        assert base_quote[0] == previous_coin or base_quote[1] == previous_coin
        coin = base_quote[0] if base_quote[1] == previous_coin else base_quote[1]
        coin_price_in_prev_coin, quantity = \
            self._get_coin_price_and_quantity_in_another_coin(market_data.get(coin_market), coin)
        return coin_price_in_prev_coin, quantity, coin

    @staticmethod
    def _path(*coins):
        return " -> ".join(coins)

    @staticmethod
    def _get_coin_price_and_quantity_in_another_coin(bidask_dict: Dict, coin: str) -> Tuple[float, float]:
        try:
            market = bidask_dict.get("Market")
        except Exception as e:
            log.debug(f"For coin {coin}")
            raise e

        base_quote = market.split("/")
        if coin == base_quote[0]:
            forward_buy = True      # We buy our coin using other coin as base
        elif coin == base_quote[1]:
            forward_buy = False     # Our coin is baee, we should reverse price
        else:
            raise AttributeError(f"Coin '{coin}' is not traded within market '{market}'")

        bid = float(bidask_dict.get("BestBid"))
        ask = float(bidask_dict.get("BestAsk"))    # bid < ask

        bid_quantity = float(bidask_dict.get("BestBidQuantity"))
        ask_quantity = float(bidask_dict.get("BestAskQuantity"))

        price = ask if forward_buy else 1 / bid
        quantity = ask_quantity if forward_buy else bid_quantity / price

        return price, quantity

    def _print_buy_info(self, coin_1: str, coin_2: str, coin_21_price: float, coin_21_quantity: float):
        if log.isEnabledFor(logging.DEBUG):
            log.debug(f"We can buy {coin_21_quantity} {coin_2}s for {coin_1} at the price {coin_21_price}")
            log.debug(f"  That means, we are spending {coin_21_quantity*coin_21_price} {coin_1} for {coin_21_quantity}"
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
