import logging
import logging.config
import sys

from .config.base import *
# from .config.staging import *
from .config.prod import *

LOG_FORMAT = "%(asctime)s %(module)-12s %(threadName)s %(levelname)-8s %(message)s"
logging.basicConfig(level=logging.WARN, format=LOG_FORMAT, stream=sys.stdout)

# todo Shut the fck up misused logging for unicorn_binance_websocket_api_manager which outputs long spam messages
# when websocket connection is lost, with CRITICAL severity

logger = logging.getLogger("patron_arby")
logger.setLevel(logging.DEBUG)

# Inject FINE level, which is more verbose than DEBUG
logging.FINE = 7
logging.addLevelName(logging.FINE, 'FINE')
logging.Logger.fine = lambda self, *args, **kwargs: self.log(logging.FINE, *args, **kwargs)
root = logging.getLogger()
logging.fine = root.fine
