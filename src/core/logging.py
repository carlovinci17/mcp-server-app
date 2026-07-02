import logging
import logging.config
from pathlib import Path

import yaml

_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "logging.yaml"
_configured = False


def configure_logging() -> None:
    global _configured
    if _configured:
        return
    with open(_CONFIG_PATH) as f:
        logging.config.dictConfig(yaml.safe_load(f))
    _configured = True


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)
