"""Tests for expardus_tracing.celery — signal handler registration."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from celery import Celery

from expardus_tracing.context import (
    clear_trace_context,
    get_trace_context,
    set_trace_context,
)
from expardus_tracing.celery import setup_celery_tracing


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
