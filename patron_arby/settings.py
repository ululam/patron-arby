import logging

from .config.base import *
# from .config.staging import *
from .config.prod import *

logging.basicConfig(
    level=logging.WARN, format="%(asctime)s %(name)-12s %(levelname)-8s %(message)s"
)

logger = logging.getLogger("patron_arby")
logger.setLevel(logging.DEBUG)

logging.FINE = 7

logging.addLevelName(logging.FINE, 'FINE')

logging.Logger.fine = lambda self, *args, **kwargs: self.log(logging.FINE, *args, **kwargs)

root = logging.getLogger()
logging.fine = root.fine
