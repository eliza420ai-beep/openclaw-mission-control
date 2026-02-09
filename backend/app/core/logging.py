"""Application logging configuration and formatter utilities."""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import UTC, datetime
from types import TracebackType
from typing import Any

from app.core.config import settings
from app.core.version import APP_NAME, APP_VERSION

TRACE_LEVEL = 5
EXC_INFO_TUPLE_SIZE = 3
logging.addLevelName(TRACE_LEVEL, "TRACE")


def _coerce_exc_info(
    value: object,
) -> (
    bool
    | tuple[type[BaseException], BaseException, TracebackType | None]
    | tuple[None, None, None]
    | BaseException
    | None
):
    if value is None:
        return None
    if isinstance(value, bool | BaseException):
        return value
    if not isinstance(value, tuple) or len(value) != EXC_INFO_TUPLE_SIZE:
        return None
    first, second, third = value
    if first is None and second is None and third is None:
        return (None, None, None)
    if (
        isinstance(first, type)
        and issubclass(first, BaseException)
        and isinstance(second, BaseException)
        and (isinstance(third, TracebackType) or third is None)
    ):
        return (first, second, third)
    return None


def _coerce_extra(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    return {str(key): item for key, item in value.items()}


def _trace(self: logging.Logger, message: str, *args: object, **kwargs: object) -> None:
    """Log a TRACE-level message when the logger is TRACE-enabled."""
    if self.isEnabledFor(TRACE_LEVEL):
        exc_info = _coerce_exc_info(kwargs.get("exc_info"))
        stack_info_raw = kwargs.get("stack_info")
        stack_info = stack_info_raw if isinstance(stack_info_raw, bool) else False
        stacklevel_raw = kwargs.get("stacklevel")
        stacklevel = stacklevel_raw if isinstance(stacklevel_raw, int) else 1
        extra = _coerce_extra(kwargs.get("extra"))
        self.log(
            TRACE_LEVEL,
            message,
            *args,
            exc_info=exc_info,
            stack_info=stack_info,
            stacklevel=stacklevel,
            extra=extra,
        )


logging.Logger.trace = _trace  # type: ignore[attr-defined]

_STANDARD_LOG_RECORD_ATTRS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
    "app",
    "version",
}


class AppLogFilter(logging.Filter):
    """Inject app metadata into each log record."""

    def __init__(self, app_name: str, version: str) -> None:
        """Initialize the filter with fixed app and version values."""
        super().__init__()
        self._app_name = app_name
        self._version = version

    def filter(self, record: logging.LogRecord) -> bool:
        """Attach app metadata fields to each emitted record."""
        record.app = self._app_name
        record.version = self._version
        return True


class JsonFormatter(logging.Formatter):
    """Formatter that serializes log records as compact JSON."""

    def format(self, record: logging.LogRecord) -> str:
        """Render a single log record into a JSON string."""
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created,
                tz=UTC,
            ).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "app": getattr(record, "app", APP_NAME),
            "version": getattr(record, "version", APP_VERSION),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack"] = self.formatStack(record.stack_info)
        for key, value in record.__dict__.items():
            if key in _STANDARD_LOG_RECORD_ATTRS or key in payload:
                continue
            payload[key] = value
        return json.dumps(payload, separators=(",", ":"), default=str)


class KeyValueFormatter(logging.Formatter):
    """Formatter that appends extra fields as `key=value` pairs."""

    # noinspection PyMethodMayBeStatic
    def format(self, record: logging.LogRecord) -> str:
        """Render a log line with appended non-standard record fields."""
        base = super().format(record)
        extras = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _STANDARD_LOG_RECORD_ATTRS
        }
        if not extras:
            return base
        extra_bits = " ".join(f"{key}={value}" for key, value in extras.items())
        return f"{base} {extra_bits}"


class AppLogger:
    """Centralized logging setup utility for the backend process."""

    _configured = False

    @classmethod
    def _resolve_level(cls) -> tuple[str, int]:
        level_name = (settings.log_level or os.getenv("LOG_LEVEL", "INFO")).upper()
        if level_name == "TRACE":
            return level_name, TRACE_LEVEL
        if level_name.isdigit():
            return level_name, int(level_name)
        levels = logging.getLevelNamesMapping()
        return level_name, levels.get(level_name, logging.INFO)

    @classmethod
    def configure(cls, *, force: bool = False) -> None:
        """Configure root logging handlers, formatters, and library levels."""
        if cls._configured and not force:
            return

        level_name, level = cls._resolve_level()

        handler = logging.StreamHandler(sys.stdout)
        handler.addFilter(AppLogFilter(APP_NAME, APP_VERSION))
        format_name = (settings.log_format or "text").lower()
        if format_name == "json":
            formatter: logging.Formatter = JsonFormatter()
        else:
            formatter = KeyValueFormatter(
                "%(asctime)s %(levelname)s %(name)s %(message)s " "app=%(app)s version=%(version)s",
            )
            if settings.log_use_utc:
                formatter.converter = time.gmtime
        handler.setFormatter(formatter)

        root = logging.getLogger()
        root.setLevel(level)
        root.handlers.clear()
        root.addHandler(handler)

        # Uvicorn & HTTP clients
        for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
            logging.getLogger(logger_name).setLevel(level)
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)

        # SQL logs only at TRACE
        sql_loggers = ("sqlalchemy", "sqlalchemy.engine", "sqlalchemy.pool")
        if level_name == "TRACE":
            for name in sql_loggers:
                logger = logging.getLogger(name)
                logger.disabled = False
                logger.setLevel(logging.INFO)
        else:
            for name in sql_loggers:
                logger = logging.getLogger(name)
                logger.disabled = True

        cls._configured = True

    @classmethod
    def get_logger(cls, name: str | None = None) -> logging.Logger:
        """Return a logger, ensuring logging has been configured."""
        if not cls._configured:
            cls.configure()
        return logging.getLogger(name)


def configure_logging() -> None:
    """Configure global application logging once during startup."""
    AppLogger.configure()
