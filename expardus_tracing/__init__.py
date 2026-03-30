"""
expardus-tracing — Shared distributed tracing library for the exPardus ecosystem.

Provides:
- **Trace context management** (contextvars-based, async-safe)
- **W3C traceparent** parsing and formatting
- **HTTP header** extraction and injection
- **Celery header** propagation and signal-based tracing
- **Structured logging** with trace context injection

Quick start::

    from expardus_tracing import (
        set_trace_context,
        get_trace_id,
        bind_context,
        get_trace_headers,
        setup_celery_tracing,
        setup_logging,
    )
"""
from __future__ import annotations

import os

# =============================================================================
# Package-level configuration (overridable at runtime via setup_logging, etc.)
# =============================================================================

SERVICE_NAME: str = os.environ.get("SERVICE_NAME", "expardus")
ENV: str = os.environ.get("ENV", "development")
RELEASE: str = os.environ.get("RELEASE", os.environ.get("COMMIT_SHA", "unknown"))

# =============================================================================
# Re-exports — context
# =============================================================================
from .context import (  # noqa: E402, F401
    TraceContext,
    generate_trace_id,
    generate_span_id,
    get_trace_context,
    set_trace_context,
    clear_trace_context,
    get_trace_id,
    get_span_id,
    get_elapsed_ms,
    set_trace_id,
    bind_context,
    trace_context_scope,
    trace_span,
    traced,
)

# =============================================================================
# Re-exports — W3C
# =============================================================================
from .w3c import (  # noqa: E402, F401
    parse_traceparent,
    parse_traceparent_full,
    format_traceparent,
    parse_tracestate,
    format_tracestate,
)

# =============================================================================
# Re-exports — headers
# =============================================================================
from .headers import (  # noqa: E402, F401
    extract_trace_from_headers,
    extract_trace_from_celery_headers,
    extract_trace_from_task_headers,
    get_trace_headers,
    get_http_trace_headers,
    get_celery_trace_headers,
    get_trace_headers_for_task,
    TRACEPARENT_HEADER,
    TRACESTATE_HEADER,
    TRACE_ID_HEADER,
    REQUEST_ID_HEADER,
    CELERY_TRACE_ID_KEY,
    CELERY_SPAN_ID_KEY,
    CELERY_TRACEPARENT_KEY,
    CELERY_TRACESTATE_KEY,
)

# =============================================================================
# Re-exports — logging
# =============================================================================
from .logging import (  # noqa: E402, F401
    TraceContextFilter,
    get_logger,
    setup_logging,
)

# =============================================================================
# Re-exports — celery
# =============================================================================
from .celery import setup_celery_tracing  # noqa: E402, F401

# =============================================================================
# Public API list
# =============================================================================
__all__ = [
    # Config
    "SERVICE_NAME",
    "ENV",
    "RELEASE",
    # Context
    "TraceContext",
    "generate_trace_id",
    "generate_span_id",
    "get_trace_context",
    "set_trace_context",
    "clear_trace_context",
    "get_trace_id",
    "get_span_id",
    "get_elapsed_ms",
    "set_trace_id",
    "bind_context",
    "trace_context_scope",
    "trace_span",
    "traced",
    # W3C
    "parse_traceparent",
    "parse_traceparent_full",
    "format_traceparent",
    "parse_tracestate",
    "format_tracestate",
    # Headers
    "extract_trace_from_headers",
    "extract_trace_from_celery_headers",
    "extract_trace_from_task_headers",
    "get_trace_headers",
    "get_http_trace_headers",
    "get_celery_trace_headers",
    "get_trace_headers_for_task",
    "TRACEPARENT_HEADER",
    "TRACESTATE_HEADER",
    "TRACE_ID_HEADER",
    "REQUEST_ID_HEADER",
    "CELERY_TRACE_ID_KEY",
    "CELERY_SPAN_ID_KEY",
    "CELERY_TRACEPARENT_KEY",
    "CELERY_TRACESTATE_KEY",
    # Logging
    "TraceContextFilter",
    "get_logger",
    "setup_logging",
    # Celery
    "setup_celery_tracing",
]
