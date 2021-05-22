import json
from decimal import Decimal
from typing import Dict, List

import boto3

from patron_arby.common.chain import AChain
from patron_arby.common.decorators import measure_execution_time, safely


class ArbitrageDao:
    def __init__(self) -> None:
        self.table = boto3.resource("dynamodb").Table("patron-arbitrage-arbitrages")
        self.firehose = boto3.client("firehose")

    @safely
    def put_profitable_arbitrage(self, arbitrage: AChain):
        return self.table.put_item(
            Item=self._convert_record(arbitrage.to_dict())
        )

    @safely
    @measure_execution_time
    def put_arbitrage_records(self, arbitrages_list: List[Dict]):
        records = [{"Data": json.dumps(r)} for r in arbitrages_list]
        self.firehose.put_record_batch(
            DeliveryStreamName='arbitrage_top',
            Records=records
        )

    def _convert_record(self, arbitrage_dict: Dict):
        # https://github.com/boto/boto3/issues/665
        # https://stackoverflow.com/questions/63026648/errormessage-class-decimal-inexact-class-decimal-rounded-while
        for k, v in arbitrage_dict.items():
            if isinstance(v, float):
                arbitrage_dict[k] = Decimal(str(v))
            if "steps" in arbitrage_dict:
                for step_dict in arbitrage_dict.get("steps"):
                    self._convert_record(step_dict)
        return arbitrage_dict
