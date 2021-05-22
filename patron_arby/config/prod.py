import os

# todo Staging/Prod config
# Defaults are test credentials which are pretty safe to expose
BINANCE_API_URL = os.environ.get(
    "BINANCE_API_URL", "https://api.binance.com/api"
)

BINANCE_WEB_SOCKET_URL = "binance.com"
