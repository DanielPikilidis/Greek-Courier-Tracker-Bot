from pydantic import BaseModel
from os import getenv

class LogConfig(BaseModel):

    LOGGER_NAME: str = getenv("LOG_NAME", "courier-tracking-bot")
    LOG_FORMAT: str = "%(asctime)s | %(message)s"
    LOG_LEVEL: str = getenv("LOG_LEVEL", "INFO").upper()
    LOG_PATH: str = getenv("LOG_PATH", "/logs")

    version: int = 1
    disable_existing_loggers: bool = False
    formatters: dict = {
        "default": {
            "()": "logging.Formatter",
            "fmt": LOG_FORMAT,
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
    }
    handlers: dict = {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
        "file": {
            "formatter": "default",
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": f"{LOG_PATH}/{LOGGER_NAME}.log",
            "when": "midnight",
            "interval": 1,
            "backupCount": 14,
        }
    }
    loggers: dict = {
        LOGGER_NAME: {"handlers": ["default", "file"], "level": LOG_LEVEL},
    }