from typing import Dict, List, Tuple

from patron_arby.common.util import current_time_ms


class MarketData:

    data: Dict = {}
    coins: List = []
    markets: List = []
    market_paths: Dict = {}

    def put(self, data_event: Dict):
        if "data" not in data_event:
            return
        if len(self.coins) == 0:
            raise AttributeError("Coins have not been set")

        symbol, record = self._to_record(data_event)
        self.data[symbol] = record

    def set_coins_and_markets(self, coins: List[str], markets: List[str]):
        self.coins = coins
        self.markets = markets
        self.market_paths = {c: [m for m in markets if m.startswith(c) or m.endswith(c)] for c in coins}

        length = 0
        for c, paths in self.market_paths.items():
            length += len(paths)
        print(f"total 1-step paths: {length}")

    def get_market_paths(self):
        return self.market_paths

    def get_coins(self) -> List[str]:
        return self.coins

    def get_markets(self) -> List[str]:
        return self.markets

    def _to_record(self, data_event: Dict) -> Tuple[str, Dict]:
        data = data_event["data"]
        market = data.get("s")
        return market, {
            "Market": market,
            "BestBid": data.get("b"),
            "BestBidQuantity": data.get("B"),
            "BestAsk": data.get("a"),
            "BestAskQuantity": data.get("A"),
            "LastUpdateTimeMs": current_time_ms()
        }

    def get(self) -> Dict:
        return self.data.copy()
