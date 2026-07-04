import logging as log
import os
from logging.handlers import TimedRotatingFileHandler


def mkdir_log():
    '''A function that creates a log directory.'''
    os.makedirs(os.path.join(os.path.dirname(__file__), "log"), exist_ok=True)


mkdir_log()

handler = TimedRotatingFileHandler(
    filename=os.path.join(os.path.dirname(__file__), "log", "server.log"),
    when="midnight",
    backupCount=7
)

log.basicConfig(
    handlers=[handler],
    level=log.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
