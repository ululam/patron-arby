import time
from typing import Dict


def current_time_ms() -> int:
    return round(time.time() * 1000)


def dict_from_obj(obj) -> Dict:
    return {k: v for k, v in obj.__dict__.items()}


def obj_from_dict(d: Dict, obj):
    for k, v in d.items():
        setattr(obj, k, v)
    return obj
