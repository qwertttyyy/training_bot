import logging
import os

from config import LOGS_PATH


def setup_logger(name: str, logfile: str):
    level = logging.INFO
    logs_format = (
        '%(asctime)s - %(levelname)s - %(funcName)s: '
        '%(lineno)d - %(message)s'
    )
    formatter = logging.Formatter(logs_format)
    handler = logging.FileHandler(os.path.join(LOGS_PATH, logfile))
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger
