import inspect
import logging
import os
from functools import wraps

from patron_arby.common.util import current_time_ms

log = logging.getLogger(os.path.basename(__file__))


def safely(func: callable):
    """
    Wraps the given function into try-catch, logging error and returning None on exception
    :param func:
    :return:
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            log.error("Unable to execute %s: %s", func.__name__, e.message if hasattr(e, 'message') else e,
                      exc_info=True)
            return None
    return wrapper


def log_execution_time(func: callable):
    """
    Executes the given function logging time execution
    :param func: function reference
    :param args: arguments for the given function
    :return:
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = current_time_ms()
        result = func(*args, **kwargs)
        log.info("Executed %s::%s() in %d ms", _obj_name(func), func.__name__, (current_time_ms() - start))
        return result

    return wrapper


def _obj_name(func):
    return os.path.basename(inspect.getfile(func))
