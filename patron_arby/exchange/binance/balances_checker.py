import logging
from decimal import Decimal
from typing import Set

from patron_arby.common.bus import Bus
from patron_arby.config.base import ARBITRAGE_COINS, BALANCE_FALL_TO_STOP_TRADING_RATIO
from patron_arby.exchange.registry import BalancesRegistry

log = logging.getLogger(__name__)

SPACE = " \t\t "

DECIMAL_PATTERN = Decimal('1.00000')


class BalancesChecker:
    def __init__(self, bus: Bus, registry: BalancesRegistry,
                 coins_of_interest: Set[str] = ARBITRAGE_COINS,
                 balance_fall_to_stop_trading_ratio: float = BALANCE_FALL_TO_STOP_TRADING_RATIO) -> None:
        super().__init__()
        self.bus = bus
        self.registry = registry
        self.coins_of_interest = coins_of_interest
        self.initial_balance = -1
        self.stop_loss_balance = -1
        self.balance_fall_to_stop_trading_ratio = balance_fall_to_stop_trading_ratio
        log.info(f"Watching balance for the following coins: {sorted(coins_of_interest)} ")
        log.info(f"Stop Loss: Trading will be forcibly stopped if those coins total balance decreases by "
                 f"{balance_fall_to_stop_trading_ratio * 100}%")

    def check_balance(self):
        if self.registry.is_empty():
            log.warning("Balances Registry is still empty, skipping run")
            return

        balances = self.registry.get_balances(self.coins_of_interest)
        total_balance_usd = sum([b.value_usd for b in balances.values() if b.value_usd])    # Protect from None

        self.log_balances()

        if self.initial_balance == -1:
            self._set_initial_balances(total_balance_usd)
            return

        self._check_stop_or_resume_trading(total_balance_usd)

    def _set_initial_balances(self, total_balance_usd: float):
        self.initial_balance = total_balance_usd
        self.stop_loss_balance = self.initial_balance * (1 - self.balance_fall_to_stop_trading_ratio)
        log.info(f"Setting initial USD balance to ${self.initial_balance}")
        log.info(f"Setting stop loss USD balance to ${self.stop_loss_balance}")

    def _check_stop_or_resume_trading(self, total_balance_usd: float):
        if total_balance_usd <= self.stop_loss_balance:
            log.critical(f"Current trading balance {total_balance_usd} fell below stop loss balance "
                         f"${self.stop_loss_balance}. Stopping trading.")
            self.bus.set_stop_trading(True)
        else:
            if self.bus.is_stop_trading():
                log.info(f"Current trading balance {total_balance_usd} raised back above threshold balance "
                         f"${self.stop_loss_balance}. Resuming trading")
                self.bus.set_stop_trading(False)

    def balances_report(self) -> str:
        if self.registry.is_empty():
            return "Balances Registry is still empty, skipping report"

        balances = self.registry.get_balances(self.coins_of_interest)
        output = "\n=== Current balances: === \n"
        for coin in sorted(self.coins_of_interest):
            bal = balances.get(coin)
            output += SPACE.join([coin, self._dec(bal.value), f"${self._dec(bal.value_usd)}", "\n"])
        total_balance_usd = sum([b.value_usd for b in balances.values() if b.value_usd])
        output += f"=== Total: ${self._dec(total_balance_usd)} BUSD === "
        return output

    def log_balances(self):
        log.info(self.balances_report())

    @staticmethod
    def _dec(v) -> str:
        if not v:
            return "0"
        return str(
            Decimal.from_float(float(v)).quantize(DECIMAL_PATTERN)
        )
