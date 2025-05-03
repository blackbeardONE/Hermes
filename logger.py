import logging
from logging.handlers import RotatingFileHandler

class ColorFormatter(logging.Formatter):
    # ANSI escape codes for colors
    COLORS = {
        'DEBUG': '\033[37m',    # White
        'INFO': '\033[36m',     # Cyan
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[41m', # Red background
    }
    RESET = '\033[0m'

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        message = super().format(record)
        return f"{color}{message}{self.RESET}"

def setup_logger(log_file='translation.log', max_bytes=5*1024*1024, backup_count=3):
    logger = logging.getLogger('converter')
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # Console handler with color formatter
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    color_formatter = ColorFormatter('%(asctime)s - %(levelname)s - %(message)s')
    ch.setFormatter(color_formatter)
    logger.addHandler(ch)

    # Rotating file handler
    fh = RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count, encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    return logger

logger = setup_logger()
