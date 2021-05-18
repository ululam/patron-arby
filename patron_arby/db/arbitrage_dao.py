import json
from decimal import Decimal
from typing import Dict, List

import boto3

from patron_arby.common.decorators import measure_execution_time, safely


class ArbitrageDao:
    def __init__(self) -> None:
        self.table = boto3.resource("dynamodb").Table("patron-arbitrage")
        self.firehose = boto3.client("firehose")

    @safely
    def put_profitable_arbitrage(self, arbitrage: Dict):
        return self.table.put_item(
            Item=self._convert_record(arbitrage)
        )

    @safely
    @measure_execution_time
    def put_arbitrage_records(self, arbitrages_list: List[Dict]):
        records = [{"Data": json.dumps(r)} for r in arbitrages_list]
        self.firehose.put_record_batch(
            DeliveryStreamName='arbitrage_top',
            Records=records
        )

    def _convert_record(self, arbitrage: Dict):
        # https://github.com/boto/boto3/issues/665
        # https://stackoverflow.com/questions/63026648/errormessage-class-decimal-inexact-class-decimal-rounded-while
        for k, v in arbitrage.items():
            if isinstance(v, float):
                arbitrage[k] = Decimal(str(v))
        return arbitrage
