import logging.config
import typing as tp

from .context import REQUEST_ID
from .settings import ServiceConfig

app_logger = logging.getLogger("app")


class RequestIDFilter(logging.Filter):
    def __init__(self, name: str = "") -> None:
        self.context_var = REQUEST_ID

        super().__init__(name)

    def filter(self, record: logging.LogRecord) -> bool:
        request_id = self.context_var.get("-")
        setattr(record, "request_id", request_id)
        return super().filter(record)


def get_config(service_config: ServiceConfig) -> tp.Dict[str, tp.Any]:
    level = service_config.log_config.level
    datetime_format = service_config.log_config.datetime_format

    config = {
        "version": 1,
        "disable_existing_loggers": True,
        "loggers": {
            "root": {
                "level": level,
                "handlers": ["console"],
                "propagate": False,
            },
            app_logger.name: {
                "level": level,
                "handlers": ["console"],
                "propagate": False,
            },
        },
        "handlers": {
            "console": {
                "formatter": "console",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "filters": ["request_id"],
            },
        },
        "formatters": {
            "console": {
                "format": (
                    'time="%(asctime)s" '
                    'level="%(levelname)s" '
                    'logger="%(name)s" '
                    'pid="%(process)d" '
                    'request_id="%(request_id)s" '
                    'message="%(message)s" '
                ),
                "datefmt": datetime_format,
            },
        },
        "filters": {
            "request_id": {"()": "requestor.log.RequestIDFilter"},
        },
    }

    return config


def setup_logging(service_config: ServiceConfig) -> None:
    config = get_config(service_config)
    logging.config.dictConfig(config)
