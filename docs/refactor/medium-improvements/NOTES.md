# Notes: Medium Improvements (M1–M6)

## Refactor Slug: `medium-improvements`

## Findings

### M1 — Idempotency Guard
- `setup_celery_tracing()` uses `weak=False` on signal connects, so closures survive GC
- Signal handlers are closures inside the function, so each call creates new handlers
- Using a module-level flag is the simplest guard pattern
- The flag needs a reset mechanism for tests (we add `_reset_celery_tracing()` as a test-only helper)

### M2 — `clear_trace_context()` in Failure Handler
- In eager mode, `task_postrun` fires after `task_failure`, so context is cleared anyway
- In production (real broker), worker crash can skip `task_postrun` entirely
- Double-clear is safe: `_trace_context.set(None)` is idempotent

### M3 — Concurrency Tests
- `ContextVar` is designed for this exact use case — tests serve as regression guards
- `pytest-asyncio` is required; confirmed available based on existing test infrastructure
- Threading test uses `ThreadPoolExecutor` — each thread gets its own ContextVar copy

### M4 — API Thin Wrapper
- The API's `tracing.py` has two extras not in the shared package:
  1. `parse_traceparent_full()` — returns `(trace_id, span_id, sampled)` tuple
  2. `sampled` parameter on `set_trace_context()` and `TraceContext`
- The shared `TraceContext` does NOT have `sampled` — we keep `parse_traceparent_full` locally
- The middleware uses `tracing.parse_traceparent_full()` and `tracing.set_trace_context(sampled=...)` 
  — these need to remain available via the thin wrapper
- Solution: thin wrapper re-exports everything from `expardus_tracing`, then adds local 
  `parse_traceparent_full()` and overrides `set_trace_context` to accept `sampled` kwarg (ignored)

### M6 — OrderedDict TTL
- `_active_spans` is a closure-local variable inside `setup_celery_tracing()`
- Replace `dict[str, Any]` with `OrderedDict[str, Any]`
- Cap at 10,000 entries — sufficient for any normal worker
- Evicted entries get a warning log

## Decisions
- M1 flag is module-level (not inside the function) for testability
- M3 uses 10 concurrent workers to stress-test isolation without being slow
- M4 keeps `parse_traceparent_full()` as local code (not added to shared package yet — that's S4)
- M6 constant `_MAX_ACTIVE_SPANS = 10_000` is not configurable (YAGNI)

## Verified
- All existing tests pass before changes (84 tests)
- `__all__` exports are complete
- No consumer imports symbols that would break
- **All 96 tests pass after changes** (84 original + 6 concurrency + 6 celery signal)
- API tests: 40/41 pass — the 1 failure (`test_logger_includes_trace_id`) is pre-existing (also fails on the old code)
- M4 change verified not to introduce regressions via `git stash` → test → `git stash pop`
