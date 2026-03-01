"""Tests for expardus_tracing.context module."""
from __future__ import annotations

import pytest

from expardus_tracing.context import (
    TraceContext,
    bind_context,
    clear_trace_context,
    generate_span_id,
    generate_trace_id,
    get_elapsed_ms,
    get_span_id,
    get_trace_context,
    get_trace_id,
    set_trace_context,
    set_trace_id,
    trace_context_scope,
    trace_span,
)


class TestGenerateIds:
    def test_trace_id_length(self):
        assert len(generate_trace_id()) == 32

    def test_trace_id_hex(self):
        tid = generate_trace_id()
        int(tid, 16)  # raises on non-hex

    def test_trace_id_unique(self):
        ids = {generate_trace_id() for _ in range(200)}
        assert len(ids) == 200

    def test_span_id_length(self):
        assert len(generate_span_id()) == 16

    def test_span_id_hex(self):
        sid = generate_span_id()
        int(sid, 16)

    def test_span_id_unique(self):
        ids = {generate_span_id() for _ in range(200)}
        assert len(ids) == 200


class TestTraceContext:
    def setup_method(self):
        clear_trace_context()

    def teardown_method(self):
        clear_trace_context()

    def test_initial_none(self):
        assert get_trace_context() is None
        assert get_trace_id() is None
        assert get_span_id() is None
        assert get_elapsed_ms() is None

    def test_set_and_get(self):
        ctx = set_trace_context(trace_id="a" * 32)
        assert get_trace_id() == "a" * 32
        assert get_span_id() is not None
        assert isinstance(ctx, TraceContext)

    def test_set_generates_ids(self):
        ctx = set_trace_context()
        assert len(ctx.trace_id) == 32
        assert len(ctx.span_id) == 16

    def test_set_with_extra(self):
        ctx = set_trace_context(task_id="T1")
        assert ctx.extra["task_id"] == "T1"

    def test_clear(self):
        set_trace_context()
        clear_trace_context()
        assert get_trace_context() is None

    def test_elapsed_ms(self):
        set_trace_context()
        ms = get_elapsed_ms()
        assert ms is not None and ms >= 0

    def test_set_trace_id_convenience(self):
        ctx = set_trace_id("b" * 32)
        assert ctx.trace_id == "b" * 32


class TestBindContext:
    def setup_method(self):
        clear_trace_context()

    def teardown_method(self):
        clear_trace_context()

    def test_bind_adds_fields(self):
        set_trace_context()
        with bind_context(user_id="42"):
            ctx = get_trace_context()
            assert ctx.extra["user_id"] == "42"
        ctx = get_trace_context()
        assert "user_id" not in ctx.extra

    def test_bind_restores_original(self):
        ctx = set_trace_context(user_id="1")
        with bind_context(user_id="2"):
            assert get_trace_context().extra["user_id"] == "2"
        assert get_trace_context().extra["user_id"] == "1"

    def test_bind_no_context(self):
        # Should not raise when no context exists
        with bind_context(x="y"):
            pass

    def test_bind_multiple_fields(self):
        set_trace_context()
        with bind_context(a="1", b="2"):
            ctx = get_trace_context()
            assert ctx.extra["a"] == "1"
            assert ctx.extra["b"] == "2"


class TestTraceContextScope:
    def setup_method(self):
        clear_trace_context()

    def teardown_method(self):
        clear_trace_context()

    def test_scope_creates_context(self):
        with trace_context_scope() as ctx:
            assert get_trace_id() == ctx.trace_id
        assert get_trace_context() is None

    def test_scope_restores_previous(self):
        outer = set_trace_context(trace_id="o" * 32)
        with trace_context_scope(trace_id="i" * 32) as inner:
            assert get_trace_id() == "i" * 32
        assert get_trace_id() == "o" * 32

    def test_scope_with_extra(self):
        with trace_context_scope(task="test") as ctx:
            assert ctx.extra["task"] == "test"


class TestTraceSpan:
    def setup_method(self):
        clear_trace_context()

    def teardown_method(self):
        clear_trace_context()

    def test_span_preserves_trace_id(self):
        parent = set_trace_context(trace_id="p" * 32)
        with trace_span("child_op") as child:
            assert child.trace_id == "p" * 32
            assert child.parent_span_id == parent.span_id
            assert child.span_id != parent.span_id
        # Parent restored
        assert get_trace_id() == "p" * 32
        assert get_span_id() == parent.span_id

    def test_span_no_parent(self):
        with trace_span("root") as ctx:
            assert ctx.trace_id is not None
            assert ctx.parent_span_id is None
        assert get_trace_context() is None

    def test_nested_spans(self):
        root = set_trace_context(trace_id="r" * 32)
        with trace_span("span1") as s1:
            with trace_span("span2") as s2:
                assert s2.trace_id == "r" * 32
                assert s2.parent_span_id == s1.span_id
            assert get_span_id() == s1.span_id
        assert get_span_id() == root.span_id
