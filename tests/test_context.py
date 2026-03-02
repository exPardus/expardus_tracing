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
    traced,
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

    def test_default_sampled(self):
        ctx = set_trace_context()
        assert ctx.sampled is True

    def test_sampled_false(self):
        ctx = set_trace_context(sampled=False)
        assert ctx.sampled is False

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


class TestTracedDecorator:
    def setup_method(self):
        clear_trace_context()

    def teardown_method(self):
        clear_trace_context()

    def test_sync_traced(self):
        """@traced should wrap a sync function in a trace_span."""
        parent = set_trace_context(trace_id="t" * 32)
        parent_span = parent.span_id

        @traced("my_operation")
        def my_func():
            ctx = get_trace_context()
            return ctx.trace_id, ctx.span_id, ctx.parent_span_id

        tid, sid, psid = my_func()
        assert tid == "t" * 32
        assert sid != parent_span  # new span
        assert psid == parent_span  # parent chained
        # After call, parent context restored
        assert get_span_id() == parent_span

    def test_sync_traced_return_value(self):
        """@traced should preserve the return value."""

        @traced("add")
        def add(a, b):
            return a + b

        assert add(2, 3) == 5

    def test_sync_traced_preserves_name(self):
        """@traced should preserve __name__ via functools.wraps."""

        @traced("op")
        def my_function():
            pass

        assert my_function.__name__ == "my_function"

    @pytest.mark.asyncio
    async def test_async_traced(self):
        """@traced should wrap an async function in a trace_span."""
        parent = set_trace_context(trace_id="a" * 32)
        parent_span = parent.span_id

        @traced("async_op")
        async def async_func():
            ctx = get_trace_context()
            return ctx.trace_id, ctx.span_id, ctx.parent_span_id

        tid, sid, psid = await async_func()
        assert tid == "a" * 32
        assert sid != parent_span
        assert psid == parent_span
        assert get_span_id() == parent_span

    @pytest.mark.asyncio
    async def test_async_traced_return_value(self):
        """@traced should preserve async return value."""

        @traced("async_add")
        async def async_add(a, b):
            return a + b

        assert await async_add(10, 20) == 30

    def test_nested_traced_decorators(self):
        """Nested @traced functions should chain spans correctly."""
        parent = set_trace_context(trace_id="n" * 32)

        inner_ctx_captured = {}

        @traced("outer")
        def outer():
            ctx = get_trace_context()
            outer_span = ctx.span_id
            inner()
            # After inner returns, outer span restored
            assert get_span_id() == outer_span
            return outer_span

        @traced("inner")
        def inner():
            ctx = get_trace_context()
            inner_ctx_captured["trace_id"] = ctx.trace_id
            inner_ctx_captured["span_id"] = ctx.span_id
            inner_ctx_captured["parent_span_id"] = ctx.parent_span_id

        outer_span = outer()
        assert inner_ctx_captured["trace_id"] == "n" * 32
        assert inner_ctx_captured["parent_span_id"] == outer_span

    def test_traced_no_parent_context(self):
        """@traced without a parent context should create a new trace."""

        @traced("orphan")
        def orphan_func():
            ctx = get_trace_context()
            return ctx.trace_id

        tid = orphan_func()
        assert tid is not None
        assert len(tid) == 32
        # After call, no context (parent was None)
        assert get_trace_context() is None

    def test_traced_with_static_extra(self):
        """@traced with static_extra should pass extra data to the span."""
        set_trace_context(trace_id="s" * 32)

        @traced("op_with_extra", component="db", layer="data")
        def my_func():
            ctx = get_trace_context()
            return ctx.extra

        extra = my_func()
        assert extra["component"] == "db"
        assert extra["layer"] == "data"
        assert extra["operation"] == "op_with_extra"
