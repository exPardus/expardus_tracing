# Parity Map: Medium Improvements (M1–M6)

## Refactor Slug: `medium-improvements`

## Overview
Implement all six medium-priority improvements from `docs/architecture/medium_and_strategic_improvements.md`.
These changes harden the shared tracing library without altering its public API contract.

---

## Feature Parity Checklist

### M1: Idempotency Guard for `setup_celery_tracing`

| # | Behavior | Before | After | Status |
|---|----------|--------|-------|--------|
| M1.1 | Single call registers signal handlers | ✅ Works | ✅ Unchanged | ☑ |
| M1.2 | Repeated calls duplicate signal handlers | ❌ Bug | ✅ Guarded — logs warning, returns early | ☑ |
| M1.3 | OTel bridge import attempt on first call | ✅ Works | ✅ Unchanged | ☑ |
| M1.4 | Module-level `_celery_tracing_initialized` flag | N/A | ✅ Added | ☑ |

### M2: `clear_trace_context()` in `task_failure` Handler

| # | Behavior | Before | After | Status |
|---|----------|--------|-------|--------|
| M2.1 | `task_postrun` clears context | ✅ Works | ✅ Unchanged | ☑ |
| M2.2 | `task_failure` clears context | ❌ Missing | ✅ Added | ☑ |
| M2.3 | Double-clear is safe (no-op) | ✅ Works | ✅ Unchanged | ☑ |

### M3: Async/Threading Isolation Tests

| # | Behavior | Before | After | Status |
|---|----------|--------|-------|--------|
| M3.1 | ContextVar isolates async tasks | ✅ Works (untested) | ✅ Tested | ☑ |
| M3.2 | ContextVar isolates threads | ✅ Works (untested) | ✅ Tested | ☑ |
| M3.3 | `trace_context_scope` across `await` | ✅ Works (untested) | ✅ Tested | ☑ |

### M4: Migrate API Repo to Shared Package

| # | Behavior | Before | After | Status |
|---|----------|--------|-------|--------|
| M4.1 | `apps.common.tracing` provides all symbols | ✅ 556-line standalone | ✅ Thin wrapper re-exporting from `expardus_tracing` | ☑ |
| M4.2 | `parse_traceparent_full()` API-specific | ✅ In standalone | ✅ Kept as local function | ☑ |
| M4.3 | `set_trace_context(sampled=…)` | ✅ API has `sampled` param | ✅ Preserved via `**extra` kwargs in shared pkg | ☑ |
| M4.4 | Middleware `from apps.common import tracing` | ✅ Works | ✅ Works (thin wrapper) | ☑ |
| M4.5 | Cloudflare service imports | ✅ Works | ✅ Works (re-exports) | ☑ |
| M4.6 | Notifications service imports | ✅ Works | ✅ Works (re-exports) | ☑ |
| M4.7 | Test imports unchanged | ✅ Works | ✅ Works (re-exports) | ☑ |

### M5: Update Extract-Tracing Parity Map

| # | Behavior | Before | After | Status |
|---|----------|--------|-------|--------|
| M5.1 | Checklist items unchecked | ❌ All ☐ | ✅ Completed items ☑ | ☑ |

### M6: TTL/Max-Size Guard on `_active_spans`

| # | Behavior | Before | After | Status |
|---|----------|--------|-------|--------|
| M6.1 | Spans stored per task_id | ✅ plain dict | ✅ OrderedDict with cap | ☑ |
| M6.2 | Orphan eviction at >10k entries | N/A | ✅ FIFO eviction with warning | ☑ |
| M6.3 | Normal operation (<10k) unaffected | ✅ Works | ✅ Unchanged | ☑ |

---

## Behavior Invariants (Must NOT Change)

1. Trace ID format: 32 hex characters
2. Span ID format: 16 hex characters
3. W3C traceparent parsing/formatting
4. ContextVar-based thread/async isolation
5. Celery header propagation keys: `trace_id`, `parent_span_id`, `traceparent`
6. HTTP header names: `x-trace-id`, `traceparent`, `x-request-id`
7. JSON structured logging format
8. OTel bridge behavior (optional, graceful degradation)
9. All existing `__all__` exports remain unchanged
10. All existing tests pass without modification
