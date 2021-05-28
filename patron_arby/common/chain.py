from dataclasses import dataclass
from typing import Dict, List, Optional

from patron_arby.common.order import OrderSide
from patron_arby.common.util import current_time_ms, dict_from_obj, obj_from_dict


@dataclass(init=False, repr=False)
class AChainStep:
    market: str
    side: OrderSide
    price: float
    volume: float

    def __init__(self, market: str, side: OrderSide, price: float, volume: float) -> None:
        super().__init__()
        self.market = market
        self.side = side
        self.price = price
        self.volume = volume

    def is_buy(self) -> bool:
        return self.side == OrderSide.BUY

    def to_dict(self) -> Dict:
        d = dict_from_obj(self)
        d["side"] = self.side.name
        return d

    def spending_coin(self) -> Optional[str]:
        """
        :return: Which coin we ACTUALLY sell at this step
        E.g. if BTC/USDT and side = BUY, we spend USDTs; if side = SELL, we spend BTCs
        """
        coins = self.market.split("/")
        if len(coins) != 2:
            return None
        return coins[1] if self.is_buy() else coins[0]

    def get_what_we_propose_volume(self) -> float:
        """
        :return: Volume of the coin which we actually spend in this step
        """
        return self.volume * self.price if self.is_buy() else self.volume

    def get_what_we_get_volume(self) -> float:
        """
        :return: Volume of the coin which we actually obtain in this step
        """
        return self.volume if self.is_buy() else self.volume * self.price

    @staticmethod
    def from_dict(d: Dict):
        o = obj_from_dict(d, AChainStep("", OrderSide.BUY, 0, 0))
        o.side = OrderSide(o.side)
        return o

    def __str__(self):
        return f"[{self.side} {self.volume} {self.market} @ {self.price}]"


@dataclass
class AChain:
    initial_coin: str = None
    steps: List[AChainStep] = None
    roi: float = 0
    profit: float = 0
    profit_usd: float = -1
    timems: int = -1
    comment: str = ""

    def __post_init__(self):
        if self.timems == -1:
            self.timems = current_time_ms()

    def uid(self) -> str:
        return f"{'-'.join([s.market.replace('/', '') for s in self.steps])}_{self.timems}"

    def hash8(self):
        return abs(hash(self.to_chain())) % (10 ** 8)

    def is_for_same_chain(self, ac) -> bool:
        if not ac:
            return False
        for stepA, stepB in zip(self.steps, ac.steps):
            if stepA.market != stepB.market:
                return False
        return True

    @property
    def initial_market(self):
        return self.steps[0].market

    def to_dict(self):
        d = dict_from_obj(self)
        d["steps"] = [s.to_dict() for s in self.steps]
        d["uid"] = self.uid()
        d["hash8"] = self.hash8()
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
