RUN_ARBITRAGE_SEARCH_PERIOD_MS = 100

# Limit arbitrage search and trading to the following coins only
ARBITRAGE_COINS = {"USDT", "DOGE", "EUR", "BTC", "BUSD", "ETH", "BNB"}  # "TRY"

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

BALANCE_UPDATER_PERIOD_SECONDS = 1
BALANCE_CHECKER_PERIOD_SECONDS = 10
POSITIVE_ARBITRAGE_STORE_PERIOD_SECONDS = 0.1

# todo Is not a constant but rather a parameter
# If we fall below that balance (sum of all arbitrage coins in USD), trading is stopped
THRESHOLD_BALANCE_USD_TO_STOP_TRADING = 250
