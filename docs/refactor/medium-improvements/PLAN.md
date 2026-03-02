# Plan: Medium Improvements (M1–M6)

## Refactor Slug: `medium-improvements`

## Target Architecture

All changes are internal to the `expardus_tracing` package or are thin-wrapper
conversions in consumer repos. No public API changes.

### What Changes
- `celery.py`: idempotency guard (M1), `clear_trace_context()` in failure handler (M2), `OrderedDict` for spans (M6)
- New file `tests/test_concurrency.py`: async + threading isolation tests (M3)
- `expardus_api/django_app/apps/common/tracing.py`: converted to thin wrapper (M4)
- `docs/refactor/extract-expardus-tracing/PARITY_MAP.md`: checklist updated (M5)

### What Stays
- All public symbols in `__all__`
- All existing test files
- All header constants and formats
- OTel bridge mechanism

## Boundaries and Non-Goals
- **Not** implementing strategic improvements (S1–S5)
- **Not** changing the package version
- **Not** modifying consumer repos other than the API's `tracing.py`
- **Not** adding new public API symbols

## Step-by-Step Migration

### Step 1: M1 — Idempotency guard in `celery.py`
Add `_celery_tracing_initialized` flag. Guard re-entry. Add tests.

### Step 2: M2 — `clear_trace_context()` in `task_failure`
Add the call at the end of `task_failure_handler`. Add test.

### Step 3: M6 — `OrderedDict` TTL guard in `celery.py`
Replace `dict` with `OrderedDict`, add max-size check. Add test.

### Step 4: M3 — Concurrency isolation tests
Create `tests/test_concurrency.py` with async and threading tests.

### Step 5: M4 — API thin wrapper migration
Replace `apps/common/tracing.py` with re-exports from `expardus_tracing`,
keeping `parse_traceparent_full()` and `sampled` parameter support locally.

### Step 6: M5 — Update parity map
Mark completed items in the extract-tracing parity map.

## Rollback Strategy
Each step is independently reversible:
- M1: remove the flag and guard
- M2: remove the added `clear_trace_context()` line
- M3: delete `tests/test_concurrency.py`
- M4: restore `apps/common/tracing.py` from git history
- M5: revert the markdown file
- M6: revert `OrderedDict` to `dict`
