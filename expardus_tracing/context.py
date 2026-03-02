"""
Trace Context Management — Core Module

Provides the central TraceContext model, context variable storage,
and helper functions for managing trace state across async/sync boundaries.

All context is stored in a ContextVar for safe concurrent access.
"""
from __future__ import annotations

import asyncio
import functools
import secrets
import time
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Callable, Generator, TypeVar

# =============================================================================
# Trace Context Model
# =============================================================================

_trace_context: ContextVar["TraceContext | None"] = ContextVar(
    "trace_context", default=None
)


@dataclass
class TraceContext:
    """Holds trace identifiers for the current execution scope."""

    trace_id: str
    span_id: str | None = None
    parent_span_id: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)
    start_time: float = field(default_factory=time.perf_counter)
    tracestate: dict[str, str] = field(default_factory=dict)
    sampled: bool = True


# =============================================================================
# ID Generation
# =============================================================================


def generate_trace_id() -> str:
    """Generate a 32-character hex trace ID (128 bits, W3C-compatible)."""
    return secrets.token_hex(16)


def generate_span_id() -> str:
    """Generate a 16-character hex span ID (64 bits, W3C-compatible)."""
    return secrets.token_hex(8)


# =============================================================================
# Context Access / Mutation
# =============================================================================


def get_trace_context() -> TraceContext | None:
    """Get the current trace context, or ``None`` if not set."""
    return _trace_context.get()


def get_trace_id() -> str | None:
    """Get the current trace ID, or ``None`` if no context."""
    ctx = get_trace_context()
    return ctx.trace_id if ctx else None


def get_span_id() -> str | None:
    """Get the current span ID, if any."""
    ctx = get_trace_context()
    return ctx.span_id if ctx else None


def get_elapsed_ms() -> float | None:
    """Get elapsed time in milliseconds since the trace started."""
    ctx = get_trace_context()
    if ctx:
        return (time.perf_counter() - ctx.start_time) * 1000
    return None


def set_trace_id(trace_id: str) -> TraceContext:
    """Convenience wrapper: set a trace context with the given trace ID."""
    return set_trace_context(trace_id=trace_id)


def set_trace_context(
    trace_id: str | None = None,
    span_id: str | None = None,
    parent_span_id: str | None = None,
    tracestate: dict[str, str] | None = None,
    sampled: bool = True,
    **extra: Any,
) -> TraceContext:
    """Set trace context for the current execution scope."""
    ctx = TraceContext(
        trace_id=trace_id or generate_trace_id(),
        span_id=span_id or generate_span_id(),
        parent_span_id=parent_span_id,
        extra=extra,
        tracestate=tracestate or {},
        sampled=sampled,
    )
    _trace_context.set(ctx)
    return ctx


def clear_trace_context() -> None:
    """Clear the current trace context."""
    _trace_context.set(None)


# =============================================================================
# Scoped helpers
# =============================================================================


@contextmanager
def bind_context(**fields: Any) -> Generator[None, None, None]:
    """
    Temporarily bind additional context fields to the current trace.

    Usage::

        with bind_context(user_id=user.id):
            do_work()
    """
    ctx = get_trace_context()
    if not ctx:
        yield
        return

    _SENTINEL = object()
    original = {k: ctx.extra.get(k, _SENTINEL) for k in fields}
    ctx.extra.update(fields)

    try:
        yield
    finally:
        for k, v in original.items():
            if v is _SENTINEL:
                ctx.extra.pop(k, None)
            else:
                ctx.extra[k] = v


@contextmanager
def trace_context_scope(
    trace_id: str | None = None,
    span_id: str | None = None,
    parent_span_id: str | None = None,
    tracestate: dict[str, str] | None = None,
    sampled: bool = True,
    **extra: Any,
) -> Generator[TraceContext, None, None]:
    """
    Context manager that creates a trace scope and restores the previous one on exit.

    Usage::

        with trace_context_scope(user_id="123") as ctx:
            logger.info("Processing", extra={"trace_id": ctx.trace_id})
    """
    previous = _trace_context.get()
    ctx = set_trace_context(
        trace_id, span_id, parent_span_id,
        tracestate=tracestate, sampled=sampled, **extra,
    )
    try:
        yield ctx
    finally:
        if previous:
            _trace_context.set(previous)
        else:
            clear_trace_context()


@contextmanager
def trace_span(
    operation: str,
    **extra: Any,
) -> Generator[TraceContext, None, None]:
    """
    Create a child span within the current trace.

    Preserves the trace ID but generates a new span ID, recording the
    current span as the parent.

    Usage::

        with trace_span("db_query", table="users") as span:
            result = db.query(...)
    """
    parent = get_trace_context()
    parent_trace_id = parent.trace_id if parent else None
    parent_span_id = parent.span_id if parent else None
    parent_tracestate = parent.tracestate if parent else None
    parent_sampled = parent.sampled if parent else True

    ctx = set_trace_context(
        trace_id=parent_trace_id,
        parent_span_id=parent_span_id,
        tracestate=parent_tracestate,
        sampled=parent_sampled,
        operation=operation,
        **extra,
    )
    try:
        yield ctx
    finally:
        # Restore parent context
        if parent:
            _trace_context.set(parent)
        else:
            clear_trace_context()


# =============================================================================
# Decorator API
# =============================================================================

_F = TypeVar("_F", bound=Callable[..., Any])


def traced(operation: str, **static_extra: Any) -> Callable[[_F], _F]:
    """
    Decorator that wraps a function in a :func:`trace_span`.

    Supports both sync and async functions. Creates a child span with the
    given operation name each time the function is called.

    Usage::

        @traced("process_order")
        def process_order(order_id):
            # ... function body is automatically spanned
            pass

        @traced("fetch_data")
        async def fetch_data(url):
            # ... async body is automatically spanned
            pass
    """

    def decorator(func: _F) -> _F:
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                with trace_span(operation, **static_extra):
                    return await func(*args, **kwargs)

            return async_wrapper  # type: ignore[return-value]
        else:

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                with trace_span(operation, **static_extra):
                    return func(*args, **kwargs)

            return sync_wrapper  # type: ignore[return-value]

    return decorator
