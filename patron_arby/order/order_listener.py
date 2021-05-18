import logging
from typing import Dict

from patron_arby.common.bus import Bus
from patron_arby.exchange.exchange_event_listener import ExchangeEventListener

log = logging.getLogger(__name__)


# https://github.com/binance-us/binance-official-api-docs/blob/master/user-data-stream.md#order-update
EVENT_KEY_TYPE = "e"
EVENT_KEY_CLIENT_ORDER_ID = "c"
EVENT_KEY_ORDER_STATUS = "X"

ORDER_STATUS_FILLED = "FILLED"


class OrderListener(ExchangeEventListener):
    def __init__(self, bus: Bus) -> None:
        super().__init__()
        self.bus = Bus

    def on_exchange_event(self, event: Dict):
        if event.get(EVENT_KEY_TYPE) != "executionReport":
            return

        client_order_id = event.get(EVENT_KEY_CLIENT_ORDER_ID)
        order_status = event.get(EVENT_KEY_ORDER_STATUS)
        log.info(f"Got notification that order {client_order_id} changed tp status {order_status}")

        if order_status == ORDER_STATUS_FILLED:
            self.on_order_executed(client_order_id)

    def on_order_executed(self, order_client_id: str):
        # Not a super solution, but there's a strong hope we won't run into hundreds of running arbitrage chains
        for chain, order_ids in self.bus.running_orders_storage.items():
            if order_client_id in order_ids:
                order_ids.remove(order_client_id)
                break
