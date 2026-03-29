"""
M2: Celery Integration Test for Trace Propagation

Tests the full lifecycle:
  1. Producer sets trace context and publishes a task with headers.
  2. Worker receives the task — prerun signal extracts trace from headers.
  3. Worker completes — postrun signal clears context.

This test does **not** require a running broker; it uses Celery's
``task_always_eager`` mode and signal hooks to simulate the pipeline.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from celery import Celery
from celery.signals import (
    before_task_publish,
    task_failure,
    task_postrun,
    task_prerun,
    task_retry,
)

from expardus_tracing import (
    clear_trace_context,
    extract_trace_from_celery_headers,
    get_celery_trace_headers,
    get_trace_context,
    get_trace_id,
    set_trace_context,
    setup_celery_tracing,
)


@pytest.fixture(autouse=True)
def _clean_context():
    clear_trace_context()
    yield
    clear_trace_context()


@pytest.fixture()
def celery_app():
    """Create a minimal Celery app for testing with eager execution."""
    app = Celery("test_worker")
    app.config_from_object(
        {
            "task_always_eager": True,
            "task_eager_propagates": True,
            "broker_url": "memory://",
            "result_backend": "cache+memory://",
        }
    )
    setup_celery_tracing(app)
    return app


class TestTracePropagationEndToEnd:
    """Full round-trip: produce → consume → verify trace continuity."""

    def test_trace_id_propagated_via_headers(self, celery_app: Celery):
        """A trace ID set before publish should appear inside the task."""
        captured: dict = {}

        @celery_app.task
        def sample_task():
            ctx = get_trace_context()
            captured["trace_id"] = ctx.trace_id if ctx else None
            captured["parent_span_id"] = ctx.parent_span_id if ctx else None
            return "ok"

        # Producer side: set trace context
        producer_ctx = set_trace_context(trace_id="a" * 32, span_id="b" * 16)
        headers = get_celery_trace_headers()

        # Dispatch with trace headers
        result = sample_task.apply(headers=headers)

        assert result.get() == "ok"
        assert captured["trace_id"] == "a" * 32

    def test_trace_context_cleared_after_task(self, celery_app: Celery):
        """After task completes, trace context should be cleared on the worker side."""

        @celery_app.task
        def clearing_task():
            return "done"

        set_trace_context(trace_id="c" * 32)
        headers = get_celery_trace_headers()

        clearing_task.apply(headers=headers)

        # The postrun handler should have cleared the context
        # (In eager mode, this runs in the same thread)
        assert get_trace_context() is None

    def test_no_trace_headers_generates_new_id(self, celery_app: Celery):
        """When no trace headers are provided, worker should generate a new trace ID."""
        captured: dict = {}

        @celery_app.task
        def no_header_task():
            ctx = get_trace_context()
            captured["trace_id"] = ctx.trace_id if ctx else None
            return "ok"

        no_header_task.apply()

        assert captured["trace_id"] is not None
        assert len(captured["trace_id"]) == 32

    def test_traceparent_header_roundtrip(self, celery_app: Celery):
        """W3C traceparent header should survive the full roundtrip."""
        captured: dict = {}

        @celery_app.task
        def tp_task():
            ctx = get_trace_context()
            if ctx:
                captured["trace_id"] = ctx.trace_id
                captured["parent_span_id"] = ctx.parent_span_id

        set_trace_context(trace_id="d" * 32, span_id="e" * 16)
        headers = get_celery_trace_headers()

        # Verify headers contain traceparent
        assert "traceparent" in headers
        tp = headers["traceparent"]
        assert tp.startswith("00-")
        assert "d" * 32 in tp

        tp_task.apply(headers=headers)

        assert captured["trace_id"] == "d" * 32

    def test_subtask_propagation(self, celery_app: Celery):
        """A child task dispatched from within a task should inherit the trace ID."""
        captured_parent: dict = {}
        captured_child: dict = {}

        @celery_app.task
        def child_task():
            ctx = get_trace_context()
            captured_child["trace_id"] = ctx.trace_id if ctx else None

        @celery_app.task
        def parent_task():
            ctx = get_trace_context()
            captured_parent["trace_id"] = ctx.trace_id if ctx else None
            # Dispatch child with propagated headers
            child_headers = get_celery_trace_headers()
            child_task.apply(headers=child_headers)

        set_trace_context(trace_id="f" * 32, span_id="1" * 16)
        headers = get_celery_trace_headers()

        parent_task.apply(headers=headers)

        assert captured_parent["trace_id"] == "f" * 32
        assert captured_child["trace_id"] == "f" * 32


class TestCeleryHeaderFormat:
    """Verify the exact header format used for Celery propagation."""

    def test_header_keys(self):
        set_trace_context(trace_id="a" * 32, span_id="b" * 16)
        headers = get_celery_trace_headers()

        assert "trace_id" in headers
        assert "parent_span_id" in headers
        assert "traceparent" in headers

    def test_header_values(self):
        set_trace_context(trace_id="a" * 32, span_id="b" * 16)
        headers = get_celery_trace_headers()

        assert headers["trace_id"] == "a" * 32
        assert headers["parent_span_id"] == "b" * 16
        assert headers["traceparent"] == f"00-{'a'*32}-{'b'*16}-01"

    def test_extract_matches_inject(self):
        """extract should recover what inject produces."""
        set_trace_context(trace_id="a" * 32, span_id="b" * 16)
        headers = get_celery_trace_headers()

        tid, psid, ts = extract_trace_from_celery_headers(headers)
        assert tid == "a" * 32
        assert psid == "b" * 16
