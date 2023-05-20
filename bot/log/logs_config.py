import logging
import os
from logging.handlers import RotatingFileHandler

from bot.config import LOGS_PATH, MAX_LOG_FILE_SIZE


def setup_logger(name: str, logfile: str):
    level = logging.INFO
    logs_format = (
        '%(asctime)s - %(levelname)s - %(funcName)s: '
        '%(lineno)d - %(message)s'
    )
    formatter = logging.Formatter(logs_format)
    log_file_path = os.path.join(LOGS_PATH, logfile)
    handler = RotatingFileHandler(
        log_file_path,
        mode='a',
        maxBytes=MAX_LOG_FILE_SIZE,
        encoding='UTF-8',
    )
    handler.setFormatter(formatter)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)

    return logger
