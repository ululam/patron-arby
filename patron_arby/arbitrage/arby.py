import logging
from typing import Dict, List, Tuple, Union

from patron_arby.arbitrage.market_data import MarketData
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

    @log_execution_time
    def find(self) -> List[Dict]:
        """
        Finds arbitrage paths
        :return: List of triangle paths with ROI, profit, and available volume
        """
        log.debug(" =========== Starting find cycle")
        start_time = current_time_ms()
        price_volume_data = self.market_data.get()
        if len(price_volume_data) == 0:
            log.warning("No data present yet, skipping finding arbitrage")
            return list()

        market_paths = self.market_data.get_market_paths()
        result = list()
        # todo Optimize: don't calculate if no new tickers arrived (remember last update time for ticker in market_data)
        for coin_a, coin_ba_paths in market_paths.items():
            for coin_b_market in coin_ba_paths:
                coin_ba_price, coin_ba_quantity, coin_b = self._calc_move_to_coin_b(coin_a=coin_a,
                    coin_ba_market=coin_b_market, price_volume_data=price_volume_data)
                if not coin_ba_price:
                    continue

                coin_bc_paths = market_paths.get(coin_b)
                if not coin_bc_paths:
                    # No further paths
                    continue

                for coin_c_market in coin_bc_paths:
                    coin_cb_price, coin_cb_quantity, coin_c = self._calc_move_to_coin_c(coin_b=coin_b,
                        coin_ba_market=coin_b_market, coin_cb_market=coin_c_market, price_volume_data=price_volume_data)
                    if not coin_cb_price:
                        continue

                    coin_ac_price, coin_ac_quantity = self._calc_move_back_to_coin_a(coin_c=coin_c,
                        coin_a=coin_a, coin_ac_market=coin_c_market, price_volume_data=price_volume_data)
                    if not coin_ac_price:
                        # No path to A via C
                        continue

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

                    if log.isEnabledFor(logging.FINE):
                        log.fine(f">>> We can run through {max_coin_a_volume_available} {coin_a}s with {roi} ROI, "
                              f"resulting in {profit} {coin_a}s profit")
                        log.fine(f"{self._path(coin_a, coin_b, coin_c, coin_a)}: = {profit}\n")

        log.debug(f" =========== End find cycle ({current_time_ms() - start_time} ms)")
        return result

    def _calc_move_to_coin_b(self, coin_a: str, coin_ba_market: str, price_volume_data: Dict) \
            -> Union[Tuple[float, float, str]]:
        """
        :param coin_a: Name of initial coin
        :param coin_ba_market: Trading symbol "COINB/COINA" (or COINA/COINB)
        :param price_volume_data: Ticker data from market_data
        :return: Tuple [Price of coin_b in coins_a, available coin_b volume, coin_b itself]
        """
        if coin_ba_market not in price_volume_data:
            # No ticker arrived yet
            return None, None, None
        coin_ba_price, coin_ba_quantity, coin_b = self._get_coin_data(coin_ba_market, coin_a, price_volume_data)
        self._print_buy_info(coin_a, coin_b, coin_ba_price, coin_ba_quantity)

        return coin_ba_price, coin_ba_quantity, coin_b

    def _calc_move_to_coin_c(self, coin_b: str, coin_ba_market: str, coin_cb_market: str, price_volume_data: Dict)\
            -> Union[Tuple[float, float, str]]:
        """
        :param coin_b: Name of the second coin in the chain
        :param coin_ba_market: Trading symbol "COINB/COINA" (or COINA/COINB)
        :param coin_cb_market: Trading symbol "COINC/COINB" (or COINB/COINC)
        :param price_volume_data: Ticker data from market_data
        :return: Tuple [Price of coin_c in coins_b, available coin_c volume, coin_c itself]
        """
        if coin_cb_market == coin_ba_market:
            # Avoid circular paths with depth 1
            return None, None, None
        if coin_cb_market not in price_volume_data:
            # No ticker arrived yet
            return None, None, None

        coin_cb_price, coin_cb_quantity, coin_c = self._get_coin_data(coin_cb_market, coin_b, price_volume_data)
        self._print_buy_info(coin_b, coin_c, coin_cb_price, coin_cb_quantity)

        return coin_cb_price, coin_cb_quantity, coin_c

    def _calc_move_back_to_coin_a(self, coin_c: str, coin_a: str, coin_ac_market: str, price_volume_data: Dict)\
            -> Union[Tuple[float, float]]:
        """
        :param coin_c:
        :param coin_a:
        :param coin_ac_market:
        :param price_volume_data:
        :return: Tuple [Price of coin_a in coins_c, available coin_a volume]
        """
        # Return to coin A
        coin_a_market_fwd = f"{coin_c}/{coin_a}"
        coin_a_market_reverse = f"{coin_a}/{coin_c}"
        if coin_a_market_fwd == coin_ac_market or coin_a_market_reverse == coin_ac_market:
            # Avoid circular path
            return None, None
        if coin_a_market_fwd in price_volume_data.keys():
            coin_a_market = coin_a_market_fwd
        elif coin_a_market_reverse in price_volume_data.keys():
            coin_a_market = coin_a_market_reverse
        else:
            # Path not present. No return to first coin
            return None, None

        coin_ac_price, coin_ac_quantity = \
            self._get_coin_price_and_quantity_in_another_coin(price_volume_data.get(coin_a_market), coin_a)
        self._print_buy_info(coin_c, coin_a, coin_ac_price, coin_ac_quantity)

        return coin_ac_price, coin_ac_quantity

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
        # todo Can I do it here, simply?
        factor = 1
        for p in prices:
            factor = factor * p
        return 1 - factor

    def _get_coin_data(self, coin_market: str, previous_coin: str, market_data: Dict) -> Tuple[float, float, str]:
        base_quote = coin_market.split("/")
        # assert base_quote[0] == previous_coin or base_quote[1] == previous_coin, f"{previous_coin} not in {
        # base_quote}"
        coin = base_quote[0] if base_quote[1] == previous_coin else base_quote[1]
        coin_price_in_prev_coin, quantity = \
            self._get_coin_price_and_quantity_in_another_coin(market_data.get(coin_market), coin)
        return coin_price_in_prev_coin, quantity, coin

    @staticmethod
    def _path(*coins):
        return " -> ".join(coins)

    def _get_coin_price_and_quantity_in_another_coin(self, bidask_dict: Dict, coin: str) -> Tuple[float, float]:
        market = bidask_dict.get("Market")

        base_quote = market.split("/")
        if coin == base_quote[0]:
            forward_buy = True      # We buy our coin using other coin as base
        elif coin == base_quote[1]:
            forward_buy = False     # Our coin is baee, we should reverse price
        else:
            raise AttributeError(f"Coin '{coin}' is not traded within market '{market}'")

        if forward_buy:
            ask = float(bidask_dict.get("BestAsk"))    # bid < ask
            ask_quantity = float(bidask_dict.get("BestAskQuantity"))
            return ask * (1 + self.default_order_fee_factor), ask_quantity

        bid = float(bidask_dict.get("BestBid"))
        bid_quantity = float(bidask_dict.get("BestBidQuantity"))
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
