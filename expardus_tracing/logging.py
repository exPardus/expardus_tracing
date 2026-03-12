"""
Structured Logging with Trace Context

Provides a logging filter that injects trace context into every log record
and a ``setup_logging`` helper for Celery workers.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from .context import get_trace_context


class TraceContextFilter(logging.Filter):
    """Logging filter that injects trace context fields into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        from . import SERVICE_NAME, ENV, RELEASE

        record.service = SERVICE_NAME  # type: ignore[attr-defined]
        record.env = ENV  # type: ignore[attr-defined]
        record.release = RELEASE  # type: ignore[attr-defined]

        ctx = get_trace_context()
        if ctx:
            record.trace_id = ctx.trace_id  # type: ignore[attr-defined]
            record.span_id = ctx.span_id or ""  # type: ignore[attr-defined]
            record.parent_span_id = ctx.parent_span_id or ""  # type: ignore[attr-defined]
            for key, value in ctx.extra.items():
                if not hasattr(record, key) and not key.startswith("_"):
                    setattr(record, key, value)
        else:
            record.trace_id = ""  # type: ignore[attr-defined]
            record.span_id = ""  # type: ignore[attr-defined]
            record.parent_span_id = ""  # type: ignore[attr-defined]

        return True


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance (convenience wrapper)."""
    return logging.getLogger(name)


def setup_logging(service_name: str | None = None) -> None:
    """
    Configure structured logging for a Celery worker.

    Call this early in worker initialisation.
    """
    import expardus_tracing as _pkg

    if service_name:
        _pkg.SERVICE_NAME = service_name

    log_json = os.environ.get("LOG_JSON_ENABLED", "true").lower() in ("1", "true", "yes")
    log_level = os.environ.get("LOG_LEVEL", "INFO")

    trace_filter = TraceContextFilter()

    handler = logging.StreamHandler()
    handler.addFilter(trace_filter)

    if log_json:
        try:
            try:
                from pythonjsonlogger.json import JsonFormatter
            except ImportError:
                from pythonjsonlogger.jsonlogger import JsonFormatter

            handler.setFormatter(
                JsonFormatter(
                    "%(levelname)s %(asctime)s %(name)s %(message)s "
                    "%(trace_id)s %(service)s %(env)s",
                    timestamp=True,
                )
            )
        except ImportError:
            handler.setFormatter(
                logging.Formatter(
                    "%(levelname)s %(asctime)s %(name)s "
                    "[trace_id=%(trace_id)s] %(message)s"
                )
            )
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(levelname)s %(asctime)s %(name)s "
                "[trace_id=%(trace_id)s] %(message)s"
            )
        )

    logging.root.handlers = [handler]
    logging.root.setLevel(log_level)

    # Reduce noise
    logging.getLogger("celery").setLevel(logging.WARNING)
    logging.getLogger("kombu").setLevel(logging.WARNING)
