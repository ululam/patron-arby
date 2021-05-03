import logging

from .config.base import *
from .config.staging import *

# from .config.prod import *

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(name)-12s %(levelname)-8s %(message)s"
)

