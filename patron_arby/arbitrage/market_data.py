import time
from typing import Dict, Tuple


class MarketData:
    pass

    data: Dict = {}

    def put(self, data_event: Dict):
        if "data" not in data_event:
            return

        symbol, record = self._to_record(data_event)
        self.data[symbol] = record

    def _to_record(self, data_event: Dict) -> Tuple[str, Dict]:
        data = data_event["data"]
        return data.get("s"), {
            "BestBid": data.get("b"),
            "BestBidQuantity": data.get("B"),
            "BestAsk": data.get("a"),
            "BestAskQuantity": data.get("A"),
            "LastUpdateTimeMs": self._now_ms()
        }

    def get(self) -> Dict:
        return self.data.copy()

    @staticmethod
    def _now_ms() -> int:
        return round(time.time() * 1000)
