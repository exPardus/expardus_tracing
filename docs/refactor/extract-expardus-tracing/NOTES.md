# NOTES.md — Refactor Decisions & Observations

## Overview

Extracted `exPardus_tracing` → `expardus_tracing` as a standalone shared
package consumed by all repos in the exPardus workspace.

---

## Key Decisions

### 1. Source Reconstruction

The original `exPardus_tracing` directory only contained `__pycache__`
bytecode — no `.py` source files remained. All modules were reconstructed
from the three full standalone implementations:

| Source                        | Lines | Used for                         |
|-------------------------------|-------|----------------------------------|
| `media_worker/tracing.py`     | 462   | context, headers, logging, celery |
| `telegram_bot/app/tracing.py` | 459   | W3C parsing, format_traceparent  |
| `api/apps/common/tracing.py`  | 556   | HTTP header extraction, extras   |

### 2. Module Layout

```
expardus_tracing/
├── context.py    # TraceContext, ContextVar, ID generation, scopes
├── w3c.py        # parse_traceparent, format_traceparent
├── headers.py    # HTTP + Celery header extract/inject, constants
├── logging.py    # TraceContextFilter, setup_logging
├── celery.py     # setup_celery_tracing (signal handlers)
└── __init__.py   # Re-exports, SERVICE_NAME/ENV/RELEASE config
```

### 3. `weak=False` on Celery Signals

Celery's `Signal.connect()` defaults to `weak=True`, storing a `weakref`
to the receiver. Because `setup_celery_tracing()` defines its handlers as
inner functions (closures), they get garbage-collected after the function
returns — silently breaking all trace propagation.

**Fix**: All 5 signal connections use `@signal.connect(weak=False)`.

This affects: `before_task_publish`, `task_prerun`, `task_postrun`,
`task_failure`, `task_retry`.

### 4. `trace_span` Reconstruction

`trace_span` was listed in bot_worker/general_worker re-exports but never
existed in any discovered source file. Implemented as a context manager
that:
- Preserves the current `trace_id`
- Generates a new `span_id`
- Records the old `span_id` as `parent_span_id`
- Restores the previous context on exit

### 5. Bot-Specific Extras Kept Local

The telegram bot's `app/tracing.py` retains three bot-specific functions
that don't belong in the shared package:

- `create_update_trace_id(update_id)` — deterministic trace ID from Telegram update ID
- `generate_idempotency_key(operation, *identifiers)` — dedup keys
- `init_otel_bot()` / `get_otel_tracer()` / `is_otel_enabled()` — bot OTel init

### 6. API Django Extras Not Migrated

The API's `apps/common/tracing.py` has Django-specific functions
(`parse_traceparent_full`, `_is_valid_trace_id`, sampled flag tracking,
request ID middleware integration) that remain local. Only the
`requirements.txt` reference was updated.

### 7. `requires-python` Lowered

Changed from `>=3.11` to `>=3.10` to match the actual runtime across all
repos (Python 3.10.1).

---

## Consumer Repo Changes

| Repo / File                         | Change                                     |
|--------------------------------------|--------------------------------------------|
| `bot_worker/tracing.py`             | `exPardus_tracing` → `expardus_tracing`  |
| `general_worker/tracing.py`         | `exPardus_tracing` → `expardus_tracing`  |
| `media_worker/tracing.py`           | 462-line standalone → thin wrapper          |
| `telegram_bot/app/tracing.py`       | 459-line standalone → wrapper + extras      |
| `bot_worker/requirements.txt`       | Package ref updated                         |
| `general_worker/requirements.txt`   | Package ref updated                         |
| `media_worker/requirements.txt`     | Package ref updated                         |
| `telegram_bot/requirements.txt`     | Package ref updated                         |
| `django_app/requirements.txt`       | Package ref updated                         |

---

## Test Summary

| Suite                            | Tests | Status |
|----------------------------------|-------|--------|
| `expardus_tracing/tests/`        | 81    | ✅ All pass |
| `celery_workers/tests/test_worker_tracing.py` | 15 | ✅ All pass |
