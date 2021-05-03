from patron_arby.arbitrage.market_data import MarketData


class Arby:
    """
    Responsible for find triangle arbitrage in market data
    """

    def __init__(self, market_data: MarketData) -> None:
        super().__init__()
        self.market_data = market_data

    def find(self):
        pass
