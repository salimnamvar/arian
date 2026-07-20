"""Logging initialization — configures stdlib logging for Arian.

Project rule
------------
Never instantiate, attach, or reconfigure handlers outside this module.
Business code must only call ``logging.getLogger(__name__)`` and emit records.
All wiring (handlers, formatters, filters, QueueListener) lives here.

Invariants
----------
1. Only the **root** logger owns output handlers.
2. Named loggers set level, clear handlers, and **propagate** to root.
3. ``configure_logging()`` is called **once** per process at startup.
   A second call with ``async_logging=True`` would start another
   QueueListener without stopping the first.

Formatting policy
-----------------
Logging format is selected internally by severity:

    Diagnostic (< INFO):  LEVEL WHEN WHERE RESOURCE : MESSAGE
    Operational (>= INFO): LEVEL WHEN RESOURCE : MESSAGE

WHERE = filename:lineno (diagnostic only)
WHEN = UTC ISO-8601 timestamp
RESOURCE = optional extra field (e.g. ``resource="model_id=bert"``)

File logging
------------
When ``LoggingConfig.log_dir`` is set, logs are written to:
    <log_dir>/arian.log

Files rotate at ``max_bytes`` with ``backup_count`` backups.
Log directory is created automatically if it does not exist.
"""

from __future__ import annotations

from datetime import datetime
from datetime import timezone
import logging
import logging.config
import logging.handlers
from pathlib import Path
import queue
from typing import Any

from arian.infrastructure.config import LoggingConfig

APPLICATION_LOGGER_NAME = "arian"

_PROPAGATING_LOGGERS = (APPLICATION_LOGGER_NAME,)

_MODULE = "arian.bootstrap.logging"

# datetime.UTC is 3.11+; timezone.utc works on 3.10+
_UTC = timezone.utc  # noqa: UP017


def _format_utc_timestamp(a_epoch_seconds: float) -> str:
    """Format Unix epoch seconds as canonical UTC ISO-8601 (microseconds + Z).

    Args:
        a_epoch_seconds: Unix epoch timestamp.

    Returns:
        Formatted string like ``2026-07-18T23:45:12.345678Z``.
    """
    dt: datetime = datetime.fromtimestamp(a_epoch_seconds, tz=_UTC)
    return dt.astimezone(_UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


class IsoUtcFormatter(logging.Formatter):
    """UTC ISO-8601 timestamp formatter."""

    def formatTime(  # a-prefix-ignore: stdlib Formatter.signature  # noqa: N802
        self,
        record: logging.LogRecord,
        datefmt: str | None = None,  # noqa: ARG002 — required by Formatter API
    ) -> str:
        """Format record creation time as canonical UTC ISO form.

        Args:
            record: Log record to format.
            datefmt: Unused, required by Formatter API.

        Returns:
            UTC ISO-8601 timestamp string.
        """
        return _format_utc_timestamp(record.created)


class ResourceFilter(logging.Filter):
    """Inject format-safe ``resource`` attribute; always admit the record."""

    def filter(self, record: logging.LogRecord) -> bool:  # a-prefix-ignore: stdlib Filter.signature
        """Attach a format-safe ``resource`` attribute; always admit the record.

        Args:
            record: Log record to filter.

        Returns:
            Always True.
        """
        resource = getattr(record, "resource", None)
        if resource:
            record.resource = f" {resource}"
        else:
            record.resource = ""
        return True


class DiagnosticLevelFilter(logging.Filter):
    """Admit Diagnostic (< INFO) records only."""

    def filter(self, record: logging.LogRecord) -> bool:  # a-prefix-ignore: stdlib Filter.signature
        """Return True for Diagnostic (< INFO) levels only.

        Args:
            record: Log record to filter.

        Returns:
            True if record level is below INFO.
        """
        return record.levelno < logging.INFO


def _build_logging_config(a_config: LoggingConfig) -> dict[str, Any]:
    """Build dictConfig: named loggers propagate to root; root owns handlers.

    Handlers:
        console_debug: diagnostic (< INFO) to stderr
        console_ops: operational (>= INFO) to stderr
        file: all levels to rotating file (if log_dir is set)

    Args:
        a_config: Validated logging configuration.

    Returns:
        Dictionary suitable for logging.config.dictConfig.
    """
    level: str = a_config.level

    handlers: dict[str, dict[str, Any]] = {
        "console_debug": {
            "class": "logging.StreamHandler",
            "level": "NOTSET",
            "formatter": "diagnostic",
            "filters": ["run_context", "diagnostic_level", "resource"],
            "stream": "ext://sys.stderr",
        },
        "console_ops": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "operational",
            "filters": ["run_context", "resource"],
            "stream": "ext://sys.stderr",
        },
    }

    root_handlers: list[str] = ["console_debug", "console_ops"]

    if a_config.log_dir is not None:
        log_dir: Path = Path(a_config.log_dir).expanduser()
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file: Path = log_dir / "arian.log"

        handlers["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "NOTSET",
            "formatter": "file",
            "filters": ["run_context", "resource"],
            "filename": str(log_file),
            "maxBytes": a_config.max_bytes,
            "backupCount": a_config.backup_count,
            "encoding": "utf-8",
        }
        root_handlers.append("file")

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "resource": {
                "()": f"{_MODULE}.ResourceFilter",
            },
            "diagnostic_level": {
                "()": f"{_MODULE}.DiagnosticLevelFilter",
            },
            "run_context": {
                "()": "arian.bootstrap.logging_filters.RunContextFilter",
            },
        },
        "formatters": {
            "diagnostic": {
                "()": f"{_MODULE}.IsoUtcFormatter",
                "format": "%(levelname)s [%(run_id)s] %(asctime)s %(filename)s:%(lineno)d%(resource)s : %(message)s",
            },
            "operational": {
                "()": f"{_MODULE}.IsoUtcFormatter",
                "format": "%(levelname)s [%(run_id)s] %(asctime)s%(resource)s : %(message)s",
            },
            "file": {
                "()": f"{_MODULE}.IsoUtcFormatter",
                "format": "%(levelname)s [%(run_id)s] %(asctime)s %(filename)s:%(lineno)d%(resource)s : %(message)s",
            },
        },
        "handlers": handlers,
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
            "handlers": root_handlers,
        },
    }


def _replace_handlers(a_logger: logging.Logger, a_handler: logging.Handler) -> None:
    """Replace all handlers on *a_logger* with *a_handler*.

    Args:
        a_logger: Logger to modify.
        a_handler: Handler to install.
    """
    a_logger.handlers.clear()
    a_logger.addHandler(a_handler)


def _enable_async_logging() -> logging.handlers.QueueListener:
    """Route root handlers through QueueHandler → QueueListener for non-blocking I/O.

    Returns:
        Running QueueListener instance.

    Raises:
        RuntimeError: If root logger has no handlers to wrap.
    """
    root: logging.Logger = logging.getLogger()
    targets: list[logging.Handler] = [
        handler for handler in root.handlers if not isinstance(handler, logging.handlers.QueueHandler)
    ]
    if not targets:
        msg = "Cannot enable async logging: root logger has no handlers"
        raise RuntimeError(msg)

    log_queue: queue.SimpleQueue[logging.LogRecord] = queue.SimpleQueue()
    queue_handler: logging.handlers.QueueHandler = logging.handlers.QueueHandler(log_queue)
    _replace_handlers(root, queue_handler)

    listener: logging.handlers.QueueListener = logging.handlers.QueueListener(
        log_queue,
        *targets,
        respect_handler_level=True,
    )
    listener.start()
    return listener


def configure_logging(a_config: LoggingConfig | None = None) -> logging.handlers.QueueListener | None:
    """Apply dictConfig + captureWarnings once at process startup.

    Returns a running ``QueueListener`` when async logging is enabled, else ``None``.

    Args:
        a_config: Logging configuration. Uses defaults if None.

    Returns:
        Running QueueListener if async_logging is enabled, None otherwise.
    """
    config: LoggingConfig = a_config or LoggingConfig()

    logging.config.dictConfig(_build_logging_config(config))
    logging.captureWarnings(True)

    listener: logging.handlers.QueueListener | None = None
    if config.async_logging:
        listener = _enable_async_logging()
    return listener
