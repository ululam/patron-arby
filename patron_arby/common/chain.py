from dataclasses import dataclass
from typing import Dict, List

from patron_arby.common.order import OrderSide
from patron_arby.common.util import current_time_ms, dict_from_obj, obj_from_dict


@dataclass(frozen=True)
class AChainStep:
    market: str
    side: OrderSide
    price: float
    volume: float

    def is_buy(self) -> bool:
        return self.side == OrderSide.BUY

    def to_dict(self) -> Dict:
        d = dict_from_obj(self)
        d["side"] = self.side.name
        return d

    @staticmethod
    def from_dict(d: Dict):
        return AChainStep(d["market"], OrderSide(d["side"]), float(d["price"]), float(d["volume"]))

    def __str__(self):
        return f"[{self.market}, {self.side}, {self.price}, {self.volume}]"


@dataclass
class AChain:
    initial_coin: str = None
    initial_market: str = None
    # todo Calculate base on market_path
    steps: List[AChainStep] = None
    roi: float = 0
    profit: float = 0
    profit_usd: float = -1
    timems: int = current_time_ms()

    def uid(self) -> str:
        return f"{'-'.join([s.market.replace('/', '') for s in self.steps])}_{self.timems}"

    def is_for_same_chain(self, ac) -> bool:
        if not ac:
            return False
        for stepA, stepB in zip(self.steps, ac.steps):
            if stepA.market != stepB.market:
                return False
        return True

    def to_dict(self):
        d = dict_from_obj(self)
        d["steps"] = [s.to_dict() for s in self.steps]
        return d

    def to_chain(self) -> str:
        return f"[{' -> '.join(s.market for s in self.steps)}]"

    def to_user_readable(self) -> str:
        return f"{self.to_chain()}, roi = {'%.4f' % (self.roi * 100)}%, profit = {'%.7f' % self.profit} " \
               f"(${'%.7f' % self.profit_usd})"

    @staticmethod
    def from_dict(d: Dict):
        ac = obj_from_dict(d, AChain())
        ac.steps = [AChainStep.from_dict(step_d) for step_d in d["steps"]]
        return ac
