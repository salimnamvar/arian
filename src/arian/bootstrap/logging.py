"""Logging initialization — configures stdlib logging for Arian.

Project rule
------------
Never instantiate, attach, or reconfigure handlers outside this module.
Business code must only call ``logging.getLogger(__name__)`` and emit records.
All wiring (handlers, formatters, filters) lives here.

Invariants
----------
1. Only the **root** logger owns output handlers.
2. Named loggers set level, clear handlers, and **propagate** to root.
3. ``configure_logging()`` is called **once** per process at startup.

Formatting policy
-----------------
Logging format is selected internally by severity:

    Diagnostic (< INFO):  LEVEL pathname:lineno : MESSAGE
    Operational (>= INFO): LEVEL : MESSAGE
"""

from __future__ import annotations

import logging
import logging.config
from typing import Any

from arian.infrastructure.config import LoggingConfig

APPLICATION_LOGGER_NAME = "arian"

_PROPAGATING_LOGGERS = (APPLICATION_LOGGER_NAME,)

_MODULE = "arian.bootstrap.logging"


class DiagnosticFormatter(logging.Formatter):
    """Format for DEBUG-level records: LEVEL pathname:lineno : MESSAGE."""

    def format(  # a-prefix-ignore: stdlib Formatter.signature
        self,
        record: logging.LogRecord,
    ) -> str:
        """Format record as diagnostic line with file location.

        Args:
            record: Log record to format.

        Returns:
            Formatted string with level, pathname, lineno, and message.
        """
        return f"{record.levelname} {record.pathname}:{record.lineno} : {record.getMessage()}"


class OperationalFormatter(logging.Formatter):
    """Format for INFO+ records: LEVEL : MESSAGE."""

    def format(  # a-prefix-ignore: stdlib Formatter.signature
        self,
        record: logging.LogRecord,
    ) -> str:
        """Format record as operational line with level and message.

        Args:
            record: Log record to format.

        Returns:
            Formatted string with level and message only.
        """
        return f"{record.levelname} : {record.getMessage()}"


class DiagnosticLevelFilter(logging.Filter):
    """Admit DEBUG-level records only (< INFO)."""

    def filter(  # a-prefix-ignore: stdlib Filter.signature
        self,
        record: logging.LogRecord,
    ) -> bool:
        """Return True for diagnostic levels only.

        Args:
            record: Log record to filter.

        Returns:
            True if record level is below INFO.
        """
        return record.levelno < logging.INFO


def _build_logging_config(a_config: LoggingConfig) -> dict[str, Any]:
    """Build dictConfig: named loggers propagate to root; root owns two handlers.

    Args:
        a_config: Validated logging configuration.

    Returns:
        Dictionary suitable for logging.config.dictConfig.
    """
    level: str = a_config.level
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "diagnostic_level": {
                "()": f"{_MODULE}.DiagnosticLevelFilter",
            },
        },
        "formatters": {
            "diagnostic": {
                "()": f"{_MODULE}.DiagnosticFormatter",
            },
            "operational": {
                "()": f"{_MODULE}.OperationalFormatter",
            },
        },
        "handlers": {
            "console_debug": {
                "class": "logging.StreamHandler",
                "level": "NOTSET",
                "formatter": "diagnostic",
                "filters": ["diagnostic_level"],
                "stream": "ext://sys.stderr",
            },
            "console_ops": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "operational",
                "stream": "ext://sys.stderr",
            },
        },
        "loggers": {
            name: {
                "level": level,
                "handlers": [],
                "propagate": True,
            }
            for name in _PROPAGATING_LOGGERS
        },
        "root": {
            "level": "WARNING",
            "handlers": ["console_debug", "console_ops"],
        },
    }


def configure_logging(a_config: LoggingConfig | None = None) -> None:
    """Apply dictConfig + captureWarnings once at process startup.

    Args:
        a_config: Logging configuration. Uses defaults if None.
    """
    config: LoggingConfig = a_config or LoggingConfig()
    logging.config.dictConfig(_build_logging_config(config))
    logging.captureWarnings(True)
