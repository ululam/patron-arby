import os

# todo Staging/Prod config
# Defaults are test credentials which are pretty safe to expose
BINANCE_API_KEY = os.environ.get(
    "BINANCE_KEY", "7UDaXRR40r5NzOCiwBtOWInJatVmrjii1AquuO4GfiTjWoGgG2RhDq4lOA8sRHyQ"
)
BINANCE_API_SECRET = os.environ.get(
    "BINANCE_SECRET", "E1vHL5OZbBHcXN3CohBAraI3KJSDDm0pC6YTEn8Y6uM3xplxQR1mZ2M5EzdET2Uo"
)
BINANCE_API_URL = os.environ.get(
    "BINANCE_API_URL", "https://testnet.binance.vision/api"
)

PAPER_API_KEY = BINANCE_API_KEY
PAPER_API_SECRET = BINANCE_API_SECRET
PAPER_API_URL = BINANCE_API_URL

BINANCE_WEB_SOCKET_URL = "binance.com-testnet"
