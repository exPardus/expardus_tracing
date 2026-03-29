"""
Celery Signal Integration

Registers Celery signal handlers for automatic trace propagation across
task publish → prerun → postrun lifecycle.
"""
from __future__ import annotations

import logging
import time
from collections import OrderedDict
from typing import Any

from .context import (
    get_trace_context,
    set_trace_context,
    clear_trace_context,
)
from .headers import (
    extract_trace_from_task_headers,
    get_trace_headers_for_task,
)

# M1: Idempotency guard — prevents duplicate signal registration
_celery_tracing_initialized: bool = False

# M6: Maximum number of active OTel spans tracked before FIFO eviction
_MAX_ACTIVE_SPANS: int = 10_000


def _reset_celery_tracing() -> None:
    """Reset the idempotency guard. **Test-only** — do not call in production."""
    global _celery_tracing_initialized
    _celery_tracing_initialized = False


def setup_celery_tracing(app: Any) -> None:
    """
    Register Celery signal handlers for automatic trace propagation.

    Call once after creating the Celery app::

        app = Celery("my_worker")
        setup_celery_tracing(app)
    """
    global _celery_tracing_initialized
    if _celery_tracing_initialized:
        logging.getLogger("celery.tracing").warning(
            "setup_celery_tracing() called more than once — skipping"
        )
        return
    _celery_tracing_initialized = True

    from celery.signals import (
        task_prerun,
        task_postrun,
        task_failure,
        task_retry,
        before_task_publish,
    )

    # Optional OTel bridge — imported from the *worker's own* ``otel_worker`` module.
    # Workers are responsible for placing ``otel_worker.py`` on ``sys.path``.
    _otel_bridge = False
    try:
        from otel_worker import (
            init_otel_worker,
            start_celery_span,
            end_celery_span,
            record_celery_metric,
        )

        from . import SERVICE_NAME as _svc_name

        init_otel_worker(_svc_name)
        _otel_bridge = True
    except ImportError:
        pass

    _logger = logging.getLogger("celery.tracing")

    # Store active OTel spans per task_id (M6: OrderedDict with max-size guard)
    _active_spans: OrderedDict[str, Any] = OrderedDict()

    # NOTE: weak=False is critical — inner functions would be GC'd otherwise
    # because they are local closures inside setup_celery_tracing.

    @before_task_publish.connect(weak=False)  # type: ignore[misc]
    def inject_trace_headers(sender: Any = None, headers: dict[str, Any] | None = None, **kwargs: Any) -> None:  # noqa: E501
        if headers is not None:
            trace_headers = get_trace_headers_for_task()
            headers.update(trace_headers)

    @task_prerun.connect(weak=False)  # type: ignore[misc]
    def task_prerun_handler(  # noqa: E501
        sender: Any = None, task_id: str | None = None, task: Any = None, args: Any = None, kwargs: Any = None, **kw: Any
    ) -> None:
        request = task.request if task else None
        headers = getattr(request, "headers", None) or {}

        trace_id, parent_span_id, tracestate = extract_trace_from_task_headers(headers)

        ctx = set_trace_context(
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            tracestate=tracestate or None,
            task_id=task_id,
            task_name=sender,
        )

        if _otel_bridge:
            try:
                _tid = task_id or ""
                span = start_celery_span(sender or "", _tid, trace_id=ctx.trace_id)
                _active_spans[_tid] = span
                # M6: Evict oldest entry if dict exceeds max size
                if len(_active_spans) > _MAX_ACTIVE_SPANS:
                    orphan_id, orphan_span = _active_spans.popitem(last=False)
                    _logger.warning(
                        "Evicted orphan span (active_spans exceeded %d)",
                        _MAX_ACTIVE_SPANS,
                        extra={"task_id": orphan_id},
                    )
            except Exception:
                pass

        _logger.info(
            "Task started",
            extra={
                "event": "task_start",
                "task_id": task_id,
                "task_name": sender,
                "queue": getattr(request, "delivery_info", {}).get("routing_key", ""),
                "trace_id": ctx.trace_id,
            },
        )

    @task_postrun.connect(weak=False)  # type: ignore[misc]
    def task_postrun_handler(  # noqa: E501
        sender: Any = None, task_id: str | None = None, task: Any = None, retval: Any = None, state: str | None = None, **kwargs: Any
    ) -> None:
        ctx = get_trace_context()
        latency_ms = (time.perf_counter() - ctx.start_time) * 1000 if ctx else 0

        if _otel_bridge and task_id in _active_spans:
            try:
                end_celery_span(
                    _active_spans.pop(task_id or ""),
                    task_name=sender or "",
                    status=state or "SUCCESS",
                    latency_ms=latency_ms,
                )
            except Exception:
                pass
        elif _otel_bridge:
            try:
                record_celery_metric(sender or "", state or "SUCCESS", latency_ms)
            except Exception:
                pass

        _logger.info(
            "Task completed",
            extra={
                "event": "task_complete",
                "task_id": task_id,
                "task_name": sender,
                "state": state,
                "latency_ms": round(latency_ms, 2),
                "trace_id": ctx.trace_id if ctx else "",
            },
        )
        clear_trace_context()

    @task_failure.connect(weak=False)  # type: ignore[misc]
    def task_failure_handler(  # noqa: E501
        sender: Any = None, task_id: str | None = None, exception: BaseException | None = None, traceback: Any = None, **kwargs: Any
    ) -> None:
        ctx = get_trace_context()
        latency_ms = (time.perf_counter() - ctx.start_time) * 1000 if ctx else 0

        if _otel_bridge and task_id in _active_spans:
            try:
                end_celery_span(
                    _active_spans.pop(task_id or ""),
                    task_name=sender or "",
                    status="FAILURE",
                    latency_ms=latency_ms,
                    error=exception,
                )
            except Exception:
                pass
        elif _otel_bridge:
            try:
                record_celery_metric(sender or "", "FAILURE", latency_ms)
            except Exception:
                pass

        _logger.error(
            "Task failed",
            extra={
                "event": "task_failure",
                "task_id": task_id,
                "task_name": sender,
                "error_type": type(exception).__name__ if exception else "Unknown",
                "error_message": str(exception)[:500] if exception else "",
                "latency_ms": round(latency_ms, 2),
                "trace_id": ctx.trace_id if ctx else "",
            },
            exc_info=True,
        )
        # M2: Clear trace context on failure to prevent leaks
        clear_trace_context()

    @task_retry.connect(weak=False)  # type: ignore[misc]
    def task_retry_handler(sender: Any = None, request: Any = None, reason: Any = None, **kwargs: Any) -> None:
        ctx = get_trace_context()
        _logger.warning(
            "Task retrying",
            extra={
                "event": "task_retry",
                "task_id": request.id if request else "",
                "task_name": sender,
                "retry_reason": str(reason)[:200] if reason else "",
                "retries": request.retries if request else 0,
                "trace_id": ctx.trace_id if ctx else "",
            },
        )

    _logger.info("Celery tracing signals registered")
