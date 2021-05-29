import logging
from typing import Dict

from patron_arby.common.chain import AChain
from patron_arby.common.util import current_time_ms
from patron_arby.config.base import ARBITRAGE_DUPLICATION_TIMEFRAME_MS

log = logging.getLogger(__name__)


class RecentArbitragersFilter:
    """
    Class to filter arbitrage duplication coming withing predefined time frame
    """

    def __init__(self, arbitrage_duplication_ttl: int = ARBITRAGE_DUPLICATION_TIMEFRAME_MS) -> None:
        super().__init__()
        self.recent_chains: Dict[str, int] = dict()
        self.arbitrage_duplication_ttl = arbitrage_duplication_ttl
        log.info(f"Arbitrages duplications timeframe = {self.arbitrage_duplication_ttl} ms")

    def register_and_return_contained(self, chain: AChain):
        """
        Registers the given chain in local cache (refreshed last_seen_time if there is a duplication)
        :param chain:
        :return: False if there was no duplicated chain, True if the given chain is a duplication of a registered one.
        """
        if not chain:
            return False
        key = self._to_key(chain)
        last_seen_time = self.recent_chains.pop(key, 0)
        now = current_time_ms()
        self.recent_chains[key] = now

        return now - last_seen_time < self.arbitrage_duplication_ttl

    def _to_key(self, chain: AChain):
        return f"{chain.to_chain()}_roi_{chain.roi}"
