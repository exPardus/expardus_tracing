# Refactor Plan: Extract expardus-tracing Package

## Refactor Slug: `extract-expardus-tracing`

## Target Architecture

```
expardus_tracing/               # Renamed from exPardus_tracing/
├── pyproject.toml              # name = "expardus-tracing"
├── expardus_tracing/           # Python package
│   ├── __init__.py             # Re-exports everything
│   ├── context.py              # TraceContext, get/set/clear, bind_context, etc.
│   ├── w3c.py                  # parse_traceparent, format_traceparent
│   ├── headers.py              # HTTP + Celery header helpers
│   ├── logging.py              # TraceContextFilter, get_logger, setup_logging
│   └── celery.py               # setup_celery_tracing (signal handlers)
└── tests/                      # Comprehensive test suite
    ├── __init__.py
    ├── test_context.py
    ├── test_w3c.py
    ├── test_headers.py
    ├── test_logging.py
    ├── test_celery_signals.py
    └── test_celery_integration.py   # M2: Celery integration test
```

## Boundaries & Non-Goals

### In Scope
- Rename exPardus_tracing → expardus_tracing
- Recreate source files (only __pycache__ exists)
- Convert media_worker/tracing.py from standalone to thin wrapper
- Update all consumer requirements.txt
- Add Celery integration test (M2)
- Add unit tests for all 3 worker tracing modules (M3)

### Out of Scope (Non-Goals)
- Changing the Django API's middleware logic
- Changing the bot's OTel initialization
- Publishing to PyPI (stays as local editable install)
- Changing otel_worker.py files (they're separate OTel bridge, not tracing core)
- Changing the API's `parse_traceparent_full()` or `sampled` flag logic

## Step-by-Step Migration Strategy

### Step 1: Create expardus_tracing package source files
- Create `expardus_tracing/` directory inside the repo
- Write `context.py`, `w3c.py`, `headers.py`, `logging.py`, `celery.py`, `__init__.py`
- Consolidate from media_worker + API implementations (superset)
- Update `pyproject.toml` to reference new package name

### Step 2: Add package tests
- Create unit tests for each module
- Create Celery integration test (M2)
- Verify all exported symbols work correctly

### Step 3: Update consumer - bot_worker and general_worker
- Change `from exPardus_tracing import ...` → `from expardus_tracing import ...`
- Update requirements.txt

### Step 4: Update consumer - media_worker
- Replace standalone tracing.py with thin wrapper
- Update requirements.txt

### Step 5: Update consumer - expardus_telegram_bot
- Replace standalone app/tracing.py with thin wrapper + bot-specific extras
- Update requirements.txt

### Step 6: Update consumer - expardus_api
- Django API tracing.py can optionally import shared code, but has enough
  Django-specific logic to stay mostly standalone. At minimum update requirements.txt.
- The API's tracing.py already works independently; we update the requirement reference.

### Step 7: Add worker tracing module unit tests (M3)
- Per-worker tests for bot_worker, general_worker, media_worker tracing.py re-export

### Step 8: Cleanup
- Remove old exPardus_tracing directory artifacts
- Remove old __pycache__ files
- Update docs

## Rollback Strategy
1. Revert the thin wrapper files to their standalone versions (available in git history)
2. Change requirements.txt back to exPardus-tracing references
3. The standalone implementations are fully functional independently
