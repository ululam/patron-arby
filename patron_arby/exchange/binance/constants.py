class Binance:
    NAME = "binance"
    # https://github.com/binance-us/binance-official-api-docs/blob/master/user-data-stream.md#order-update
    EVENT_KEY_TYPE = "e"

    EVENT_KEY_ORDER_ID = "i"
    EVENT_KEY_ORDER_SIDE = "S"
    EVENT_KEY_ORDER_STATUS = "X"
    EVENT_KEY_SYMBOL = "s"
    EVENT_KEY_QUANTITY = "q"
    EVENT_KEY_PRICE = "p"
    EVENT_KEY_CLIENT_ORDER_ID = "c"
    EVENT_KEY_ORIGINAL_CLIENT_ORDER_ID = "C"
    EVENT_KEY_EVENT_TIME = "E"

    ORDER_STATUS_FILLED = "FILLED"
    ORDER_STATUS_CANCELLED = "CANCELLED"

    REST_KEY_ORDER_ID = "orderId"
    REST_KEY_SYMBOL = "symbol"
    REST_KEY_CLIENT_ORDER_ID = "clientOrderId"
    REST_KEY_PRICE = "price"
    REST_KEY_ORIG_QUANTITY = "origQty"
    REST_KEY_STATUS = "status"
    REST_KEY_SIDE = "side"
    REST_KEY_TYPE = "type"
    REST_KEY_FILLS = "fills"
    REST_KEY_TRANSACT_TIME = "transactTime"

    USD_COINS = {"BUSD", "USDT", "USDC"}


ORDER_CANCELATOR_RUN_PERIOD_MS = 1_000
ORDER_CANCELATOR_ORDER_TTL_MS = 5_000
ARBY_RUN_PERIOD_MS = 100
