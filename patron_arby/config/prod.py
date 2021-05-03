import os

# todo Staging/Prod config
# Defaults are test credentials which are pretty safe to expose
BINANCE_API_KEY = os.environ.get(
    "BINANCE_KEY", "GKtYDTApqmmniyvZvt1Nuhlr0tilllHVRB6WWB9XUgtBAYBeu0ueYkXa3cmFXlvc"
)
BINANCE_API_SECRET = os.environ.get(
    "BINANCE_SECRET", "s4Rc93YjDGylGSuVJ2eFq5APWtL1mTUwsJ3KRKYSHx7w6uzxuksK2xaEv2kw4Ika"
)
BINANCE_API_URL = os.environ.get(
    "BINANCE_API_URL", "https://api.binance.com"
)
