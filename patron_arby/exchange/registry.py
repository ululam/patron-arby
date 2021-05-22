from typing import Dict, Optional


class BalancesRegistry:
    balances = dict()

    def get_balances(self, exchange_name: str) -> Optional[Dict[str, float]]:
        return self.balances.get(exchange_name)

    def set_balances(self, exchange_name: str, balances: Dict[str, float]):
        self.balances[exchange_name] = balances
