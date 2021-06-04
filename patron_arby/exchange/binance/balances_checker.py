import logging
from decimal import Decimal
from typing import Set

from patron_arby.common.bus import Bus
from patron_arby.config.base import (
    ARBITRAGE_COINS,
    THRESHOLD_BALANCE_USD_TO_STOP_TRADING,
)
from patron_arby.exchange.registry import BalancesRegistry

log = logging.getLogger(__name__)

SPACE = " \t\t "

DECIMAL_PATTERN = Decimal('1.00000')


class BalancesChecker:
    def __init__(self, bus: Bus, registry: BalancesRegistry,
                 coins_of_interest: Set[str] = ARBITRAGE_COINS,
                 stop_trading_balance_threshold_usd: float = THRESHOLD_BALANCE_USD_TO_STOP_TRADING) -> None:
        super().__init__()
        self.bus = bus
        self.registry = registry
        self.coins_of_interest = coins_of_interest
        self.stop_trading_balance_threshold_usd = stop_trading_balance_threshold_usd
        log.info(f"Watching balance for the following coins: {sorted(coins_of_interest)} ")
        log.info(f"Trading will be forcibly stopped if those coins balance falls below "
                 f"${stop_trading_balance_threshold_usd}")

    def check_balance(self) -> float:
        balances = self.registry.get_balances(self.coins_of_interest)
        total_balance_usd = sum([b.value_usd for b in balances.values()])
        if total_balance_usd <= self.stop_trading_balance_threshold_usd:
            log.critical(f"Current trading balance {total_balance_usd} fell below STOP TRADING limit "
                         f"${self.stop_trading_balance_threshold_usd}. Trading is stopped")
            self.bus.set_stop_trading(True)
        else:
            if self.bus.is_stop_trading():
                log.info(f"Current trading balance {total_balance_usd} raised above STOP TRADING limit "
                         f"${self.stop_trading_balance_threshold_usd}. Resuming trading")
                self.bus.set_stop_trading(False)

        self.log_balances()

        return total_balance_usd

    def balances_report(self) -> str:
        balances = self.registry.get_balances(self.coins_of_interest)
        output = "\n=== Current balances: === \n"
        for coin in sorted(self.coins_of_interest):
            bal = balances.get(coin)
            output += SPACE.join([coin, self._dec(bal.value), f"${self._dec(bal.value_usd)}", "\n"])
        total_balance_usd = sum([b.value_usd for b in balances.values()])
        output += f"=== Total: ${self._dec(total_balance_usd)} BUSD === "
        return output

    def log_balances(self):
        log.info(self.balances_report())

    @staticmethod
    def _dec(v) -> str:
        return str(
            Decimal.from_float(float(v)).quantize(DECIMAL_PATTERN)
        )
