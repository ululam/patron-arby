import os

# todo Staging/Prod config
# Defaults are test credentials which are pretty safe to expose
BINANCE_API_KEY = os.environ.get(
    "BINANCE_KEY", "eKvuOFrMJWhDGcRAdeqAA8ADl0gkbcve54j6RceSnu9IQU0zCZGbcauxixV3uN7J"
)
BINANCE_API_SECRET = os.environ.get(
    "BINANCE_SECRET", "lW3X1UjOUanOYFrATr6opAqPOj3GCGDToFeGRRDb63ABdXtpcXvhWPamCHBD7zqq"
)
BINANCE_API_URL = os.environ.get(
    "BINANCE_API_URL", "https://testnet.binance.vision/api"
)

PAPER_API_KEY = BINANCE_API_KEY
PAPER_API_SECRET = BINANCE_API_SECRET
PAPER_API_URL = BINANCE_API_URL

BINANCE_WEB_SOCKET_URL = "binance.com-testnet"
