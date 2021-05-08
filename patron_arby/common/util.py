import time


def current_time_ms() -> int:
    return round(time.time() * 1000)
