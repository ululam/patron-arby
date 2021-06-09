from enum import Enum

RUN_ARBITRAGE_SEARCH_PERIOD_MS = 100

# Limit arbitrage search and trading to the following coins only
ARBITRAGE_COINS = {"USDT", "DOGE", "EUR", "BTC", "BUSD", "ETH", "BNB"}  # "TRY"
# If true, PetroniusArbiter will fire arbitrage chains as soon as he finds it. Otherwise, he will go till the end,
# gather all profitable arbitrages together, and fire as a single message
ARBITRAGE_FIRE_CHAIN_ASAP = False

# If true, TradeManager will fire orders only for the most profitable arbitrage in list he gets.
# If false, he will fire all arbitrage chain, one by one, in order of profitability
TRADE_MANAGER_FIRE_ONLY_TOP_ARBITRAGE = True

# If True, arbitrage chains are sorted by ROI. Otherwise, sorted by profit
TRADE_MANAGER_SORT_ARBITRAGE_BY_ROI = True

# If profit is less than that value, USD, we don't put arbitrage orders
ORDER_PROFIT_THRESHOLD_USD = 0.01

# Maximum ratio (%) of balance that can participate in a single order
MAX_BALANCE_RATIO_PER_SINGLE_ORDER = 1.0    # 100%

# If we see same arbitrage chain, with the same profit, coming within the given time frame, we throttle it
ARBITRAGE_DUPLICATION_TIMEFRAME_MS = 1_000

# How many OrderExecutor threads are run
ORDER_EXECUTORS_NUMBER = 3

# Max records kinesis allowes to write in a batch
KINESIS_MAX_BATCH_SIZE = 500

# Default coin for USD. Is Binance-specific at the moment
DEFAULT_USD_COIN = "BUSD"

BALANCE_UPDATER_PERIOD_SECONDS = 5
BALANCE_CHECKER_PERIOD_SECONDS = 10

BALANCE_CHECKER_DEVIATION_FROM_MEAN_TO_REBALANCE = 0.75
POSITIVE_ARBITRAGE_STORE_PERIOD_SECONDS = 0.1

# todo Is not a constant but rather a parameter
# If we fall below that balance (sum of all arbitrage coins in USD), trading is stopped
THRESHOLD_BALANCE_USD_TO_STOP_TRADING = 300

# How long order should live before get cancelled
ORDER_CANCELATOR_ORDER_TTL_MS = 3_000

ORDER_CANCELATOR_RUN_PERIOD_MS = ORDER_CANCELATOR_ORDER_TTL_MS


class BinanceTimeInForce(Enum):
    GOOD_TILL_CANCELLED = "GTC"
    IMMEDIATE_OR_CANCEL = "IOC"
    FILL_OR_KILL = "FOK"
    GTX = 'GTX'  # Good Till Crossing, Post only order


# @see https://github.com/binance-us/binance-official-api-docs/blob/master/rest-api.md#new-order--trade for details
# BINANCE_LIMIT_ORDER_TIME_IN_FORCE = "FOK"
BINANCE_LIMIT_ORDER_DEFAULT_TIME_IN_FORCE: BinanceTimeInForce = BinanceTimeInForce.IMMEDIATE_OR_CANCEL
