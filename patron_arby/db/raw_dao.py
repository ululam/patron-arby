import json
from typing import Dict

import boto3


class RawDao:
    def __init__(self) -> None:
        self.firehose = boto3.client("firehose")

    def save_ticker(self, ticker: Dict):
        self.firehose.put_record(
            DeliveryStreamName='raw_market_data',
            Record={"Data": json.dumps(ticker)}
        )
