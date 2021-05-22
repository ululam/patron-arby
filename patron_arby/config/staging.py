import os

# todo Staging/Prod config
# Defaults are test credentials which are pretty safe to expose
BINANCE_PAPER_API_KEY = os.environ.get(
    "BINANCE_KEY", "eKvuOFrMJWhDGcRAdeqAA8ADl0gkbcve54j6RceSnu9IQU0zCZGbcauxixV3uN7J"
)
BINANCE_PAPER_API_SECRET = os.environ.get(
    "BINANCE_SECRET", "lW3X1UjOUanOYFrATr6opAqPOj3GCGDToFeGRRDb63ABdXtpcXvhWPamCHBD7zqq"
)
BINANCE_PAPER_API_URL = os.environ.get(
    "BINANCE_API_URL", "https://testnet.binance.vision/api"
)
