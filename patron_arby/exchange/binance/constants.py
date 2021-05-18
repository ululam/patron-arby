class Binance:
    # https://github.com/binance-us/binance-official-api-docs/blob/master/user-data-stream.md#order-update
    EVENT_KEY_TYPE = "e"

    EVENT_KEY_ORDER_SIDE = "S"
    EVENT_KEY_ORDER_STATUS = "X"
    EVENT_KEY_SYMBOL = "s"
    EVENT_KEY_QUANTITY = "q"
    EVENT_KEY_PRICE = "p"
    EVENT_KEY_CLIENT_ORDER_ID = "c"

    ORDER_STATUS_FILLED = "FILLED"
