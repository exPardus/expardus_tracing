# Parity Map: Extract expardus-tracing Package

## Refactor Slug: `extract-expardus-tracing`

## Overview
Rename `exPardus_tracing` → `expardus_tracing`, recreate missing source files,
consolidate 4 near-identical tracing implementations into the shared package,
and add comprehensive tests.

---

## Feature Parity Checklist

### Context Management (`context.py`)

| # | Feature | Current Location(s) | Expected After | Status |
|---|---------|---------------------|----------------|--------|
| C1 | `TraceContext` dataclass | API, media_worker, bot tracing.py | `expardus_tracing.context` | ☑ |
| C2 | `generate_trace_id()` (32 hex) | API, media_worker, bot tracing.py | `expardus_tracing.context` | ☑ |
| C3 | `generate_span_id()` (16 hex) | API, media_worker, bot tracing.py | `expardus_tracing.context` | ☑ |
| C4 | `get_trace_context()` | All | `expardus_tracing.context` | ☑ |
| C5 | `set_trace_context()` | All | `expardus_tracing.context` | ☑ |
| C6 | `clear_trace_context()` | All | `expardus_tracing.context` | ☑ |
| C7 | `get_trace_id()` | All | `expardus_tracing.context` | ☑ |
| C8 | `get_span_id()` | API, bot | `expardus_tracing.context` | ☑ |
| C9 | `get_elapsed_ms()` | API, bot | `expardus_tracing.context` | ☑ |
| C10 | `set_trace_id()` (convenience) | media_worker | `expardus_tracing.context` | ☑ |
| C11 | `bind_context()` context manager | All | `expardus_tracing.context` | ☑ |
| C12 | `trace_context_scope()` | API | `expardus_tracing.context` | ☑ |
| C13 | `trace_span()` | Referenced in re-exports | `expardus_tracing.context` | ☑ |

### W3C Traceparent (`w3c.py`)

| # | Feature | Current Location(s) | Expected After | Status |
|---|---------|---------------------|----------------|--------|
| W1 | `parse_traceparent()` | All | `expardus_tracing.w3c` | ☑ |
| W2 | `format_traceparent()` | API, bot | `expardus_tracing.w3c` | ☑ |
| W3 | `parse_traceparent_full()` (with sampled flag) | API only | API-local (not in shared pkg) | ☑ |

### Header Helpers (`headers.py`)

| # | Feature | Current Location(s) | Expected After | Status |
|---|---------|---------------------|----------------|--------|
| H1 | `extract_trace_from_headers()` | API | `expardus_tracing.headers` | ☑ |
| H2 | `extract_trace_from_celery_headers()` | API, bot, media_worker | `expardus_tracing.headers` | ☑ |
| H3 | `extract_trace_from_task_headers()` | media_worker | `expardus_tracing.headers` | ☑ |
| H4 | `get_trace_headers()` | API, bot | `expardus_tracing.headers` | ☑ |
| H5 | `get_http_trace_headers()` | media_worker | `expardus_tracing.headers` | ☑ |
| H6 | `get_celery_trace_headers()` | API, bot | `expardus_tracing.headers` | ☑ |
| H7 | `get_trace_headers_for_task()` | media_worker | `expardus_tracing.headers` | ☑ |
| H8 | Header constants (`TRACEPARENT_HEADER` etc.) | All | `expardus_tracing.headers` | ☑ |

### Logging (`logging.py`)

| # | Feature | Current Location(s) | Expected After | Status |
|---|---------|---------------------|----------------|--------|
| L1 | `TraceContextFilter` | API, media_worker | `expardus_tracing.logging` | ☑ |
| L2 | `get_logger()` | API | `expardus_tracing.logging` | ☑ |
| L3 | `setup_logging()` | media_worker | `expardus_tracing.logging` | ☑ |

### Celery Integration (`celery.py`)

| # | Feature | Current Location(s) | Expected After | Status |
|---|---------|---------------------|----------------|--------|
| CL1 | `setup_celery_tracing()` | media_worker | `expardus_tracing.celery` | ☑ |

### Configuration

| # | Feature | Current Location(s) | Expected After | Status |
|---|---------|---------------------|----------------|--------|
| CF1 | `SERVICE_NAME` | All | `expardus_tracing` (module-level) | ☑ |
| CF2 | `ENV` | All | `expardus_tracing` (module-level) | ☑ |
| CF3 | `RELEASE` | All | `expardus_tracing` (module-level) | ☑ |

---

## Consumer Repos & Import Paths

| Consumer | Current Import | After Refactor | Status |
|----------|---------------|----------------|--------|
| `celery_backround_workers/bot_worker/tracing.py` | `from exPardus_tracing import ...` | `from expardus_tracing import ...` (thin wrapper stays) | ☑ |
| `celery_backround_workers/general_worker/tracing.py` | `from exPardus_tracing import ...` | `from expardus_tracing import ...` (thin wrapper stays) | ☑ |
| `celery_backround_workers/media_worker/tracing.py` | Full standalone (462 lines) | Thin wrapper around `expardus_tracing` | ☑ |
| `expardus_telegram_bot/app/tracing.py` | Full standalone (459 lines) | Thin wrapper + bot-specific extras | ☑ |
| `expardus_api/django_app/apps/common/tracing.py` | Full standalone (556 lines) | Thin wrapper + API-specific extras | ☑ (M4) |
| All `requirements.txt` files | `exPardus-tracing @ file:///...exPardus_tracing` | `expardus-tracing @ file:///...expardus_tracing` | ☑ |

---

## Behavior That Must NOT Change

1. Trace ID format: 32 hex characters
2. Span ID format: 16 hex characters
3. W3C traceparent parsing/formatting
4. ContextVar-based thread/async isolation
5. Celery header propagation keys: `trace_id`, `parent_span_id`, `traceparent`
6. HTTP header names: `x-trace-id`, `traceparent`, `x-request-id`
7. JSON structured logging format
8. OTel bridge behavior (optional, graceful degradation)

## Intentional Changes

1. Package name: `exPardus-tracing` → `expardus-tracing`
2. Import path: `exPardus_tracing` → `expardus_tracing`
3. media_worker/tracing.py: standalone → thin wrapper
4. bot app/tracing.py: standalone → thin wrapper + bot-specific extras

---

## High-Risk Areas

1. **Import resolution**: Workers use `from tracing import X` — the local `tracing.py` wrapper must re-export everything correctly.
2. **Celery signal registration**: `setup_celery_tracing()` imports `otel_worker` relatively — must still work after extraction.
3. **Missing source files**: The `exPardus_tracing/` package only has `__pycache__` — source files must be reconstructed correctly.
4. **Django-specific code**: API's `tracing.py` has `parse_traceparent_full()` and `sampled` flag — these stay API-local.
5. **Bot-specific code**: `create_update_trace_id()`, `generate_idempotency_key()`, OTel bot init — stays bot-local.

## Acceptance Criteria

- [x] `expardus_tracing` package installable via `pip install -e ./expardus_tracing`
- [x] All consumer `tracing.py` files import from `expardus_tracing`
- [x] All requirements.txt reference `expardus-tracing`
- [x] Package exports all symbols listed in parity table
- [x] Celery integration test passes (M2)
- [x] Unit tests for all 3 worker tracing modules pass (M3)
- [x] Existing API test_tracing.py passes (40/41 — 1 pre-existing failure unrelated to refactor)
- [x] No references to `exPardus_tracing` remain in code (only in docs/history)
