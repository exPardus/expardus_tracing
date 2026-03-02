"""
Tests for async and threading isolation of ContextVar-based trace context (M3).

Verifies that ContextVar provides proper isolation across:
- concurrent asyncio tasks
- concurrent threads (ThreadPoolExecutor)
- trace_context_scope across await boundaries
"""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor

import pytest

from expardus_tracing.context import (
    clear_trace_context,
    get_trace_id,
    set_trace_context,
    trace_context_scope,
)


@pytest.fixture(autouse=True)
def _clean_context():
    clear_trace_context()
    yield
    clear_trace_context()


class TestAsyncIsolation:
    """Verify that concurrent asyncio tasks have isolated trace contexts."""

    @pytest.mark.asyncio
    async def test_concurrent_tasks_isolated(self):
        """10 concurrent async tasks should each see only their own trace ID."""
        results: dict[int, str | None] = {}

        async def worker(i: int) -> None:
            tid = f"{i:032x}"
            set_trace_context(trace_id=tid)
            await asyncio.sleep(0.01)  # Yield control to other tasks
            results[i] = get_trace_id()
            clear_trace_context()

        await asyncio.gather(*(worker(i) for i in range(10)))

        for i in range(10):
            assert results[i] == f"{i:032x}", (
                f"Task {i} saw trace_id={results[i]}, expected {i:032x}"
            )

    @pytest.mark.asyncio
    async def test_scope_restores_across_await(self):
        """trace_context_scope should restore correctly across await boundaries."""
        outer = set_trace_context(trace_id="a" * 32)

        async def inner_work():
            with trace_context_scope(trace_id="b" * 32) as inner_ctx:
                assert get_trace_id() == "b" * 32
                await asyncio.sleep(0.01)
                assert get_trace_id() == "b" * 32

        await inner_work()
        assert get_trace_id() == "a" * 32

    @pytest.mark.asyncio
    async def test_nested_async_scopes(self):
        """Nested trace_context_scope in async code should stack correctly."""
        results: list[str | None] = []

        async def level2():
            with trace_context_scope(trace_id="c" * 32):
                await asyncio.sleep(0.005)
                results.append(get_trace_id())

        async def level1():
            with trace_context_scope(trace_id="b" * 32):
                results.append(get_trace_id())
                await level2()
                results.append(get_trace_id())

        set_trace_context(trace_id="a" * 32)
        await level1()
        results.append(get_trace_id())

        assert results == ["b" * 32, "c" * 32, "b" * 32, "a" * 32]


class TestThreadIsolation:
    """Verify that concurrent threads have isolated trace contexts."""

    def test_threads_isolated(self):
        """10 concurrent threads should each see only their own trace ID."""
        results: dict[int, str | None] = {}

        def worker(i: int) -> None:
            tid = f"{i:032x}"
            set_trace_context(trace_id=tid)
            import time

            time.sleep(0.01)
            results[i] = get_trace_id()
            clear_trace_context()

        with ThreadPoolExecutor(max_workers=5) as pool:
            list(pool.map(worker, range(10)))

        for i in range(10):
            assert results[i] == f"{i:032x}", (
                f"Thread {i} saw trace_id={results[i]}, expected {i:032x}"
            )

    def test_thread_does_not_inherit_parent_context(self):
        """Threads spawned via ThreadPoolExecutor should NOT inherit the parent's context."""
        set_trace_context(trace_id="parent" + "0" * 26)
        child_result: dict[str, str | None] = {}

        def child_worker():
            child_result["trace_id"] = get_trace_id()

        with ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(child_worker).result()

        # ThreadPoolExecutor threads don't inherit ContextVars by default
        assert child_result["trace_id"] is None

    def test_main_thread_unaffected_by_child(self):
        """Setting context in a child thread should not affect the main thread."""
        set_trace_context(trace_id="main" + "0" * 28)

        def child_worker():
            set_trace_context(trace_id="child" + "0" * 27)

        with ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(child_worker).result()

        assert get_trace_id() == "main" + "0" * 28
