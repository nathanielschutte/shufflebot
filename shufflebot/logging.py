
import os, logging
from logging.config import fileConfig

log_config = 'config/logging_config.ini'

def logging_setup():
    if os.path.isfile(log_config):
        fileConfig(log_config)
        logger = logging.getLogger(__name__)
        logger.debug(f'Loading logging config file: {log_config}')
    else:
        logger = logging.getLogger(__name__)
        logger.addHandler(logging.NullHandler())