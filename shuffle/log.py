import logging
import os

def shuffle_logger(name='shuffle'):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s [%(levelname)s] |   %(message)s')
    file_handle = logging.FileHandler('/var/log/shuffle/out.log' if os.getenv('SHUFFLE_ENV') != 'local' else './out.log', encoding='utf-8')
    file_handle.setFormatter(formatter)
    logger.addHandler(file_handle)
    console_handle = logging.StreamHandler()
    console_handle.setFormatter(formatter)
    logger.addHandler(console_handle)

    return logger
