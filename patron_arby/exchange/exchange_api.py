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
    def put_order(self, o: Order) -> object:
        """
        Puts the given order to the market
        :param o:
        :return: Order id.
                todo ATM, its not clear how the response should look like in generic case, for all exchanges
        """
        pass
