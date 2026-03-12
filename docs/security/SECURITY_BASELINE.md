# Security Baseline - expardus_tracing

**Last Updated:** July 25, 2026

## Baseline Checklist

### Cryptographic Safety
- [x] Trace IDs generated with `secrets.token_hex(16)` (128-bit CSPRNG)
- [x] Span IDs generated with `secrets.token_hex(8)` (64-bit CSPRNG)
- [x] No use of `random` module for security-relevant values

### Input Validation
- [x] W3C traceparent: length checks, hex validation, all-zero rejection, version check
- [x] Tracestate: rejects keys starting with `_` (defense-in-depth)
- [x] Tracestate: max 32 members per W3C spec
- [x] Tracestate: max 256-char key and value lengths
- [x] Fail-safe defaults: invalid headers return `(None, None, True)` (sampled=True)
- [x] Celery header values coerced to `str()` for type safety

### Context Isolation
- [x] `contextvars.ContextVar` for async-safe trace context storage
- [x] `clear_trace_context()` called in both `task_postrun` and `task_failure` Celery signals
- [x] No cross-task context leakage possible
- [x] Memory bounded: `_MAX_ACTIVE_SPANS = 10000` with FIFO eviction

### Log Safety
- [x] `TraceContextFilter` checks `not hasattr(record, key)` before `setattr()`
- [x] Keys starting with `_` rejected from extra dict injection into log records
- [x] Built-in LogRecord attributes cannot be overwritten

### Dependency Safety
- [x] Zero mandatory dependencies
- [x] Optional deps pinned with minimum versions (`celery>=5.3`, `python-json-logger>=2.0`)
- [x] `py.typed` marker for type checker compatibility

### Signal Safety (Celery)
- [x] `weak=False` on all Celery signal connections (prevents GC disconnection)
- [x] Signals registered: `before_task_publish`, `task_prerun`, `task_postrun`, `task_failure`
- [x] Header injection uses plain dict update (no pickle)

### Testing
- [x] Traceparent parsing: valid, invalid, edge cases (all-zero, wrong version, short IDs)
- [x] Tracestate: dunder key rejection, member count limits, key/value length limits
- [x] Logging filter: extra field injection, dunder key rejection, no-overwrite guard
- [x] Celery signal integration: context propagation, cleanup on failure
- [x] Concurrency tests: context isolation across threads/coroutines
- [x] Public API exports verification
