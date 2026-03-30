"""Tests for expardus_tracing.logging module."""
from __future__ import annotations

import logging

import pytest

from expardus_tracing.context import clear_trace_context, set_trace_context
from expardus_tracing.logging import TraceContextFilter, get_logger, setup_logging


class TestTraceContextFilter:
    def setup_method(self):
        clear_trace_context()

    def teardown_method(self):
        clear_trace_context()

    def test_filter_no_context(self):
        filt = TraceContextFilter()
        record = logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None)
        result = filt.filter(record)
        assert result is True
        assert record.trace_id == ""  # type: ignore[attr-defined]
        assert record.span_id == ""  # type: ignore[attr-defined]

    def test_filter_with_context(self):
        set_trace_context(trace_id="a" * 32, span_id="b" * 16)
        filt = TraceContextFilter()
        record = logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None)
        filt.filter(record)
        assert record.trace_id == "a" * 32  # type: ignore[attr-defined]
        assert record.span_id == "b" * 16  # type: ignore[attr-defined]

    def test_filter_adds_service_info(self):
        filt = TraceContextFilter()
        record = logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None)
        filt.filter(record)
        assert hasattr(record, "service")
        assert hasattr(record, "env")
        assert hasattr(record, "release")

    def test_filter_extra_fields(self):
        set_trace_context(user_id="42")
        filt = TraceContextFilter()
        record = logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None)
        filt.filter(record)
        assert record.user_id == "42"  # type: ignore[attr-defined]

    def test_filter_does_not_overwrite_existing(self):
        set_trace_context(name="trace_name")
        filt = TraceContextFilter()
        record = logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None)
        # name is already on LogRecord
        original_name = record.name
        filt.filter(record)
        assert record.name == original_name

    def test_filter_rejects_underscore_prefixed_extra_keys(self):
        """SEC-ET-001: Extra keys starting with _ must not be set on log records."""
        set_trace_context(__class__="evil", _private="hidden", safe_key="ok")
        filt = TraceContextFilter()
        record = logging.LogRecord("test", logging.INFO, "", 0, "msg", (), None)
        original_class = record.__class__
        filt.filter(record)
        # Dunder keys must NOT be injected
        assert record.__class__ is original_class
        assert not hasattr(record, "_private")
        # Safe keys must be injected
        assert record.safe_key == "ok"  # type: ignore[attr-defined]


class TestGetLogger:
    def test_returns_logger(self):
        log = get_logger("mymodule")
        assert isinstance(log, logging.Logger)
        assert log.name == "mymodule"


class TestSetupLogging:
    def test_setup_configures_root(self):
        """setup_logging should add a handler with TraceContextFilter to root logger."""
        original_handlers = logging.root.handlers[:]
        try:
            setup_logging(service_name="test-service")
            assert any(
                any(isinstance(f, TraceContextFilter) for f in h.filters)
                for h in logging.root.handlers
            )
        finally:
            logging.root.handlers = original_handlers
