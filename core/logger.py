"""Logger: 滚动日志到 ~/.liodesktop/logs/app.log"""
import logging
import os
from logging.handlers import RotatingFileHandler

DATA_DIR = os.path.expanduser("~/.liodesktop")
LOG_DIR = os.path.join(DATA_DIR, "logs")

def get_logger(name="liodesktop"):
    os.makedirs(LOG_DIR, exist_ok=True)
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        fh = RotatingFileHandler(os.path.join(LOG_DIR, "app.log"),
                                 maxBytes=1_000_000, backupCount=3, encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        logger.addHandler(fh)
        sh = logging.StreamHandler()
        sh.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        logger.addHandler(sh)
    return logger
