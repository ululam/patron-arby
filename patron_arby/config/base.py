RUN_ARBITRAGE_SEARCH_PERIOD_MS = 100

# Limit arbitrage search and trading to the following coins only
ARBITRAGE_COINS = {"USDT", "DOGE", "EUR", "BTC", "BUSD", "ETH", "BNB"}  # "TRY"

# If profit is less than that value, USD, we don't put arbitrage orders
ORDER_PROFIT_THRESHOLD_USD = 0.01

# Maximum ratio (%) of balance that can participate in a single order
MAX_BALANCE_RATIO_PER_SINGLE_ORDER = 0.6    # 60%
