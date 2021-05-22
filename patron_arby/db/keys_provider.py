import base64
import json
from typing import Tuple

import boto3


class KeysProvider:
    def __init__(self, profile_name: str = None) -> None:
        super().__init__()
        # Create a Secrets Manager client
        if profile_name:
            session = boto3.session.Session(profile_name=profile_name)
        else:
            session = boto3.session.Session()
        self.client = session.client(
            service_name="secretsmanager",
            region_name="us-east-1"
        )

    def get_exchange_api_keys(self, exchange_name: str) -> Tuple[str, str]:
        keys_json = self.get_secret(f"{exchange_name.upper()}_API_KEYS")
        keys_dict = json.loads(keys_json)
        return keys_dict.get(f"{exchange_name.upper()}_API_KEY"), keys_dict.get(f"{exchange_name.upper()}_API_SECRET")

    def get_secret(self, secret_name: str):
        get_secret_value_response = self.client.get_secret_value(SecretId=secret_name)
        # Decrypts secret using the associated KMS CMK.
        # Depending on whether the secret is a string or binary, one of these fields will be populated.
        if 'SecretString' in get_secret_value_response:
            return get_secret_value_response['SecretString']

        return base64.b64decode(get_secret_value_response['SecretBinary'])
