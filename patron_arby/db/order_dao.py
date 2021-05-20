from decimal import Decimal
from typing import Dict, Optional

import boto3
from botocore.exceptions import ClientError

from patron_arby.common.decorators import safely
from patron_arby.common.order import Order
from patron_arby.common.util import current_time_ms


class OrderDao:
    def __init__(self) -> None:
        self.table = boto3.resource("dynamodb").Table("patron-arbitrage-orders")
        # self.firehose = boto3.client("firehose")

    def get_order(self, client_order_id: str) -> Optional[Order]:
        try:
            record = self.table.get_item(Key={"client_order_id": client_order_id})
            if not record.get("Item"):
                return None
            return Order.from_dict(record.get("Item"))
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                return None
            raise e

    @safely
    def put_order(self, order: Order):
        prev_order = self.get_order(order.client_order_id)
        if prev_order:
            prev_order_dict = prev_order.to_dict()
            # Preserve/set values explicitly
            prev_order_dict["created_at"] = prev_order.created_at
            prev_order_dict["updated_at"] = current_time_ms()
            prev_order_dict["arbitrage_id"] = prev_order.arbitrage_id if prev_order.arbitrage_id else order.arbitrage_id
            return self.table.put_item(
                Item=self._convert_floats_to_decimals(prev_order_dict)
            )

        order.created_at = current_time_ms()
        return self.table.put_item(
            Item=self._convert_floats_to_decimals(order.to_dict())
        )

    @staticmethod
    def _convert_floats_to_decimals(order: Dict):
        # https://github.com/boto/boto3/issues/665
        # https://stackoverflow.com/questions/63026648/errormessage-class-decimal-inexact-class-decimal-rounded-while
        for k, v in order.items():
            if isinstance(v, float):
                order[k] = Decimal(str(v))
        return order
