"""
HTTP and Celery Header Helpers

Provides extraction and injection of trace context from/to HTTP request
headers and Celery task message headers.
"""
from __future__ import annotations

from typing import Any, Mapping

from .context import (
    get_trace_context,
    generate_span_id,
)
from .w3c import format_traceparent, parse_traceparent, parse_traceparent_full, parse_tracestate, format_tracestate

# =============================================================================
# Header name constants
# =============================================================================

TRACEPARENT_HEADER = "traceparent"
TRACESTATE_HEADER = "tracestate"
TRACE_ID_HEADER = "x-trace-id"
REQUEST_ID_HEADER = "x-request-id"

# Celery message header keys
CELERY_TRACE_ID_KEY = "trace_id"
CELERY_SPAN_ID_KEY = "parent_span_id"
CELERY_TRACEPARENT_KEY = "traceparent"
CELERY_TRACESTATE_KEY = "tracestate"


# =============================================================================
# HTTP Header Extraction
# =============================================================================


def extract_trace_from_headers(
    headers: Mapping[str, str] | None,
) -> tuple[str | None, str | None, dict[str, str], bool]:
    """
    Extract trace context from HTTP headers.

    Priority:
        1. W3C ``traceparent``
        2. ``X-Trace-ID``
        3. ``X-Request-ID``

    Returns:
        (trace_id, parent_span_id, tracestate, sampled) — parent_span_id may be ``None``,
        tracestate is an empty dict if not present, sampled defaults to True.
    """
    if not headers:
        return None, None, {}, True

    normalised = {k.lower(): v for k, v in headers.items()}

    # Parse tracestate (always, regardless of traceparent source)
    tracestate = parse_tracestate(normalised.get(TRACESTATE_HEADER))

    # W3C traceparent
    traceparent = normalised.get(TRACEPARENT_HEADER)
    if traceparent:
        tid, psid, sampled = parse_traceparent_full(traceparent)
        if tid:
            return tid, psid, tracestate, sampled

    # X-Trace-ID
    trace_id = normalised.get(TRACE_ID_HEADER)
    if trace_id and _is_valid_trace_id(trace_id):
        return trace_id.lower(), None, tracestate, True

    # X-Request-ID
    request_id = normalised.get(REQUEST_ID_HEADER)
    if request_id and _is_valid_trace_id(request_id):
        return request_id.lower(), None, tracestate, True

    return None, None, tracestate, True


def _is_valid_trace_id(trace_id: str) -> bool:
    """Accept 16 or 32 hex chars (reject all-zeros per W3C spec)."""
    if len(trace_id) not in (16, 32):
        return False
    try:
        int(trace_id, 16)
    except ValueError:
        return False
    # W3C spec: all-zero trace IDs are invalid
    return trace_id != "0" * len(trace_id)


# =============================================================================
# HTTP Header Injection
# =============================================================================


def get_trace_headers() -> dict[str, str]:
    """
    Get propagation headers for outbound HTTP requests.

    Returns ``traceparent``, ``tracestate`` (if present), and ``X-Trace-ID``
    for compatibility.
    """
    ctx = get_trace_context()
    if not ctx:
        return {}

    headers: dict[str, str] = {TRACE_ID_HEADER: ctx.trace_id}
    if ctx.span_id:
        try:
            headers[TRACEPARENT_HEADER] = format_traceparent(
                ctx.trace_id, ctx.span_id, sampled=ctx.sampled
            )
        except (ValueError, TypeError):
            pass  # Skip traceparent if trace context has invalid values
    if ctx.tracestate:
        headers[TRACESTATE_HEADER] = format_tracestate(ctx.tracestate)
    return headers


def get_http_trace_headers() -> dict[str, str]:
    """Alias for :func:`get_trace_headers` — used by Celery workers calling APIs."""
    return get_trace_headers()


# =============================================================================
# Celery Header Extraction
# =============================================================================


def extract_trace_from_celery_headers(
    headers: Mapping[str, Any] | None,
) -> tuple[str | None, str | None, dict[str, str], bool]:
    """
    Extract trace context from Celery task headers.

    Returns:
        (trace_id, parent_span_id, tracestate, sampled)
    """
    if not headers:
        return None, None, {}, True

    # Extract tracestate regardless of traceparent source
    tracestate_raw = headers.get(CELERY_TRACESTATE_KEY)
    tracestate = parse_tracestate(str(tracestate_raw)) if tracestate_raw else {}

    traceparent = headers.get(CELERY_TRACEPARENT_KEY)
    if traceparent:
        tid, psid, sampled = parse_traceparent_full(str(traceparent))
        if tid:
            return tid, psid, tracestate, sampled

    trace_id = headers.get(CELERY_TRACE_ID_KEY)
    parent_span_id = headers.get(CELERY_SPAN_ID_KEY)

    if trace_id:
        trace_id_str = str(trace_id)
        if not _is_valid_trace_id(trace_id_str):
            trace_id_str = None  # type: ignore[assignment]
        if trace_id_str:
            return trace_id_str, str(parent_span_id) if parent_span_id else None, tracestate, True

    return None, None, tracestate, True


# Alias used by media_worker (same behaviour)
extract_trace_from_task_headers = extract_trace_from_celery_headers


# =============================================================================
# Celery Header Injection
# =============================================================================


def get_celery_trace_headers() -> dict[str, str]:
    """
    Get trace headers for Celery task dispatch.

    Usage::

        task.apply_async(args=[...], headers=get_celery_trace_headers())
    """
    ctx = get_trace_context()
    if not ctx:
        return {}

    headers: dict[str, str] = {CELERY_TRACE_ID_KEY: ctx.trace_id}
    if ctx.span_id:
        headers[CELERY_SPAN_ID_KEY] = ctx.span_id
        try:
            headers[CELERY_TRACEPARENT_KEY] = format_traceparent(
                ctx.trace_id, ctx.span_id, sampled=ctx.sampled
            )
        except (ValueError, TypeError):
            pass  # Skip traceparent if trace context has invalid values
    if ctx.tracestate:
        headers[CELERY_TRACESTATE_KEY] = format_tracestate(ctx.tracestate)
    return headers


def get_trace_headers_for_task() -> dict[str, str]:
    """Alias for :func:`get_celery_trace_headers` (worker→sub-task propagation)."""
    return get_celery_trace_headers()
