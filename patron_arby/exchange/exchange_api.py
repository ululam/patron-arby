import abc
from abc import ABC
from typing import Dict, List, Optional

from patron_arby.common.order import Order


class ExchangeApi(ABC):
    @abc.abstractmethod
    def get_all_markets(self) -> List[str]:
        """
        :return: List of all trading markets (aka "symbols"), e.g.: BTCUSD, ETHBTC etc.
        """
        pass

    @abc.abstractmethod
    def get_trade_fees(self) -> Dict[str, float]:
        """
        :return: Dict of {market -> fee}. Usually we suggest that we use "taker" commissions for arbitrage,
                but that's market-dependent
        """
        pass

    @abc.abstractmethod
    def get_default_trade_fee(self) -> Optional[float]:
        """
        :return: Default trading fee associated with account, None if not defined
        """
        pass

    @abc.abstractmethod
    def get_balances(self) -> Dict[str, float]:
        """
        :return: {coin -> balance}
        """
        pass

    def get_latest_prices(self) -> Dict[str, float]:
        """
        :return: {market -> price}
        """
        pass

    @abc.abstractmethod
    def put_order(self, o: Order) -> Order:
        """
        Puts the given order to the market as LIMIT order
        :param o:
        :return: result order as replied from the exchange
                todo ATM, its not clear how the response should look like in generic case, for all exchanges
        """
        pass

    @abc.abstractmethod
    def put_market_order(self, o: Order) -> Order:
        """
        Puts the given order to the market  as LIMIT order
        :param o:
        :return: result order as replied from the exchange
        """
        pass

    @abc.abstractmethod
    def get_open_orders(self) -> List[Order]:
        """
        :return: List of all open orders for the current account
        """
        pass

    @abc.abstractmethod
    def cancel_order(self, symbol: str, order_id: str) -> object:
        """
        Cancels the given order
        :param symbol:
        :param order_id:
        :return: Exchange-specific response
        """
        pass
