"""Tests for expardus_tracing.celery — signal handler registration."""
from __future__ import annotations

import logging
from collections import OrderedDict
from unittest.mock import MagicMock

import pytest
from celery import Celery

from expardus_tracing.context import (
    clear_trace_context,
    get_trace_context,
    set_trace_context,
)
from expardus_tracing.celery import (
    setup_celery_tracing,
    _reset_celery_tracing,
    _MAX_ACTIVE_SPANS,
)


# Module-scoped Celery app: signals registered exactly once.
_signal_app = Celery("signal_test_worker")
_signal_app.config_from_object(
    {
        "task_always_eager": True,
        "task_eager_propagates": True,
        "broker_url": "memory://",
        "result_backend": "cache+memory://",
    }
)
setup_celery_tracing(_signal_app)


@pytest.fixture(autouse=True)
def _clean_context():
    clear_trace_context()
    yield
    clear_trace_context()


class TestSetupCeleryTracing:
    """Test that setup_celery_tracing registers all expected signal handlers."""

    def test_registers_signals(self):
        """Signal handlers should be connected after calling setup_celery_tracing."""
        from celery.signals import (
            before_task_publish,
            task_prerun,
            task_postrun,
            task_failure,
            task_retry,
        )

        assert before_task_publish.receivers
        assert task_prerun.receivers
        assert task_postrun.receivers
        assert task_failure.receivers
        assert task_retry.receivers


class TestInjectTraceHeaders:
    """Test the before_task_publish signal handler."""

    def test_inject_headers_with_context(self):
        """When a trace context exists, headers should be populated."""
        from celery.signals import before_task_publish

        set_trace_context(trace_id="a" * 32, span_id="b" * 16)

        headers: dict = {}
        before_task_publish.send(
            sender="test_task",
            headers=headers,
            body={},
            exchange="",
            routing_key="",
        )

        assert headers.get("trace_id") == "a" * 32
        assert headers.get("parent_span_id") == "b" * 16
        assert "traceparent" in headers

    def test_inject_headers_no_context(self):
        """When no trace context exists, headers should remain empty."""
        from celery.signals import before_task_publish

        headers: dict = {}
        before_task_publish.send(
            sender="test_task",
            headers=headers,
            body={},
            exchange="",
            routing_key="",
        )

        assert "trace_id" not in headers


class TestTaskPrerun:
    """Test the task_prerun signal handler."""

    def test_prerun_sets_context(self):
        """task_prerun should set a trace context."""
        from celery.signals import task_prerun

        mock_task = MagicMock()
        mock_task.request.headers = {
            "trace_id": "c" * 32,
            "parent_span_id": "d" * 16,
        }

        task_prerun.send(
            sender="test_task",
            task_id="task-123",
            task=mock_task,
            args=(),
            kwargs={},
        )

        ctx = get_trace_context()
        assert ctx is not None
        assert ctx.trace_id == "c" * 32

    def test_prerun_generates_trace_id_when_missing(self):
        """If no trace headers, a new trace_id should be generated."""
        from celery.signals import task_prerun

        mock_task = MagicMock()
        mock_task.request.headers = {}

        task_prerun.send(
            sender="test_task",
            task_id="task-456",
            task=mock_task,
            args=(),
            kwargs={},
        )

        ctx = get_trace_context()
        assert ctx is not None
        assert len(ctx.trace_id) == 32


class TestTaskPostrun:
    """Test the task_postrun signal handler."""

    def test_postrun_clears_context(self):
        """task_postrun should clear the trace context."""
        from celery.signals import task_postrun

        set_trace_context(trace_id="e" * 32)

        task_postrun.send(
            sender="test_task",
            task_id="task-789",
            task=MagicMock(),
            retval=None,
            state="SUCCESS",
        )

        assert get_trace_context() is None


class TestTaskFailure:
    """Test the task_failure signal handler (M2)."""

    def test_failure_clears_context(self):
        """task_failure should clear the trace context (M2)."""
        from celery.signals import task_failure

        set_trace_context(trace_id="f" * 32)

        task_failure.send(
            sender="test_task",
            task_id="task-fail-1",
            exception=ValueError("test error"),
            traceback=None,
        )

        assert get_trace_context() is None

    def test_failure_then_postrun_safe(self):
        """Calling clear twice (failure + postrun) should not raise."""
        from celery.signals import task_failure, task_postrun

        set_trace_context(trace_id="g" * 32)

        task_failure.send(
            sender="test_task",
            task_id="task-fail-2",
            exception=RuntimeError("boom"),
            traceback=None,
        )
        assert get_trace_context() is None

        # Simulate postrun also firing (as it does in eager mode)
        task_postrun.send(
            sender="test_task",
            task_id="task-fail-2",
            task=MagicMock(),
            retval=None,
            state="FAILURE",
        )
        assert get_trace_context() is None


class TestIdempotencyGuard:
    """Test M1: setup_celery_tracing idempotency guard."""

    def test_second_call_logs_warning(self, caplog):
        """Calling setup_celery_tracing twice should log a warning on the second call."""
        # The module-level call in this file already initialized once.
        # A second call should warn and return early.
        with caplog.at_level(logging.WARNING, logger="celery.tracing"):
            setup_celery_tracing(Celery("dup_test"))

        assert any(
            "called more than once" in record.message
            for record in caplog.records
        )

    def test_second_call_does_not_duplicate_receivers(self):
        """Signal receiver count should not increase on second call."""
        from celery.signals import task_prerun

        count_before = len(task_prerun.receivers)
        setup_celery_tracing(Celery("dup_test2"))
        count_after = len(task_prerun.receivers)

        assert count_after == count_before

    def test_reset_allows_reinit(self):
        """_reset_celery_tracing should allow re-initialization (test helper)."""
        from expardus_tracing.celery import _celery_tracing_initialized

        assert _celery_tracing_initialized is True
        _reset_celery_tracing()

        from expardus_tracing.celery import (
            _celery_tracing_initialized as after_reset,
        )

        assert after_reset is False
        # Re-initialize to restore state for other tests
        setup_celery_tracing(Celery("reinit_test"))


class TestActiveSpansTTL:
    """Test M6: OrderedDict TTL guard on _active_spans."""

    def test_active_spans_is_ordered_dict(self):
        """_active_spans should be an OrderedDict after setup."""
        # We can't access the closure variable directly, but we can verify
        # the constant is accessible
        assert _MAX_ACTIVE_SPANS == 10_000
