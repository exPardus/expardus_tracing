# expardus-tracing

Shared distributed tracing library for the **exPardus** ecosystem.
**exPardus** is a universal marketplace platform for buying and selling anything, built to expand into new services over time.

Provides zero-dependency, `ContextVar`-based trace context management with optional Celery and structured logging integrations.

## Install

```bash
# Editable (development)
pip install -e /path/to/expardus_tracing

# With Celery support
pip install -e "/path/to/expardus_tracing[celery]"

# With JSON structured logging
pip install -e "/path/to/expardus_tracing[json-logging]"

# All extras (development)
pip install -e "/path/to/expardus_tracing[dev]"
```

## Quick Start

```python
from expardus_tracing import (
    set_trace_context,
    get_trace_id,
    get_trace_headers,
    trace_span,
    bind_context,
)

# Set up a trace (e.g., in middleware)
ctx = set_trace_context(trace_id="abc123...", span_id="def456...")

# Get the current trace ID anywhere in the call stack
print(get_trace_id())  # "abc123..."

# Get headers for outbound HTTP requests
headers = get_trace_headers()
# {"x-trace-id": "abc123...", "traceparent": "00-abc123...-def456...-01"}

# Create child spans
with trace_span("db_query", table="users") as span:
    # span.trace_id preserved, span.span_id is new
    result = db.query(...)

# Bind temporary context fields
with bind_context(user_id="42"):
    # All log records in this scope include user_id=42
    do_work()
```

## Celery Integration

```python
from celery import Celery
from expardus_tracing import setup_celery_tracing, setup_logging

app = Celery("my_worker")

# Set up structured logging (call once at startup)
setup_logging(service_name="my_worker")

# Register signal handlers for automatic trace propagation (call once)
setup_celery_tracing(app)
```

This automatically:
- Injects trace headers into outbound task messages (`before_task_publish`)
- Extracts trace context on task receipt (`task_prerun`)
- Logs task start/complete/failure/retry events with `trace_id` and `latency_ms`
- Clears trace context after each task (`task_postrun`)

## Modules

| Module | Purpose |
|--------|---------|
| `context` | `TraceContext` dataclass, `ContextVar` storage, ID generation, `bind_context`, `trace_span` |
| `w3c` | W3C `traceparent` header parsing and formatting |
| `headers` | HTTP and Celery header extraction/injection, header name constants |
| `logging` | `TraceContextFilter` for stdlib logging, `setup_logging()` |
| `celery` | `setup_celery_tracing()` — Celery signal handlers |

## Public API

### Context Management

| Function | Description |
|----------|-------------|
| `set_trace_context(trace_id?, span_id?, parent_span_id?, **extra)` | Set trace context for current scope |
| `get_trace_context()` | Get current `TraceContext` or `None` |
| `get_trace_id()` | Get current trace ID or `None` |
| `get_span_id()` | Get current span ID or `None` |
| `get_elapsed_ms()` | Milliseconds since trace started |
| `clear_trace_context()` | Clear current context |
| `set_trace_id(trace_id)` | Convenience: set context with just a trace ID |
| `bind_context(**fields)` | Context manager: temporarily add extra fields |
| `trace_context_scope(...)` | Context manager: create scope, restore previous on exit |
| `trace_span(operation, **extra)` | Context manager: create child span within current trace |
| `generate_trace_id()` | Generate 32-char hex trace ID |
| `generate_span_id()` | Generate 16-char hex span ID |

### W3C

| Function | Description |
|----------|-------------|
| `parse_traceparent(header)` | Parse `traceparent` → `(trace_id, parent_span_id)` or `(None, None)` |
| `format_traceparent(trace_id, span_id, sampled=True)` | Format a `traceparent` header value |

### Headers

| Function | Description |
|----------|-------------|
| `extract_trace_from_headers(headers)` | Extract trace from HTTP headers (priority: traceparent → x-trace-id → x-request-id) |
| `extract_trace_from_celery_headers(headers)` | Extract trace from Celery task headers |
| `get_trace_headers()` | Get `{"x-trace-id": ..., "traceparent": ...}` for outbound HTTP |
| `get_http_trace_headers()` | Alias for `get_trace_headers()` |
| `get_celery_trace_headers()` | Get `{"trace_id": ..., "parent_span_id": ..., "traceparent": ...}` for Celery dispatch |

### Constants

| Constant | Value |
|----------|-------|
| `TRACEPARENT_HEADER` | `"traceparent"` |
| `TRACE_ID_HEADER` | `"x-trace-id"` |
| `REQUEST_ID_HEADER` | `"x-request-id"` |
| `CELERY_TRACE_ID_KEY` | `"trace_id"` |
| `CELERY_SPAN_ID_KEY` | `"parent_span_id"` |
| `CELERY_TRACEPARENT_KEY` | `"traceparent"` |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVICE_NAME` | `"expardus"` | Service name injected into logs |
| `ENV` | `"development"` | Environment name (production, staging, etc.) |
| `RELEASE` | `COMMIT_SHA` or `"unknown"` | Release/commit identifier |
| `LOG_JSON_ENABLED` | `"true"` | Enable JSON structured logging |
| `LOG_LEVEL` | `"INFO"` | Root log level |

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ -v --cov=expardus_tracing
```

## License

MIT
