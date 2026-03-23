# Security Baseline - expardus_tracing

**Last Updated:** July 25, 2026
**Audit Date:** July 25, 2026
**Overall Security Posture:** GOOD ✅

## Executive Summary

`expardus_tracing` is a small shared library with zero mandatory dependencies and a minimal attack surface. It uses cryptographically secure random generation (`secrets.token_hex`), async-safe context propagation (`contextvars.ContextVar`), robust W3C traceparent parsing with fail-safe defaults, and proper Celery signal lifecycle management. No Critical or High severity findings.

---

## Security Controls Verified

| Control | Status | Evidence |
|---------|--------|----------|
| CSPRNG for trace/span IDs | ✅ PASS | `secrets.token_hex(16)` / `secrets.token_hex(8)` — cryptographically secure |
| Async-safe context storage | ✅ PASS | Uses `contextvars.ContextVar` — isolated per async task/coroutine |
| W3C traceparent validation | ✅ PASS | Length checks, hex validation, all-zero rejection, version check, fail-safe `(None, None, True)` on error |
| Tracestate key sanitization | ✅ PASS | Rejects `_`-prefixed keys, enforces 32-member limit, 256-char caps |
| Celery context lifecycle | ✅ PASS | `task_postrun` and `task_failure` both clear context; prevents cross-task leakage |
| Memory leak prevention | ✅ PASS | `_MAX_ACTIVE_SPANS = 10000` with FIFO eviction in span stack |
| Celery signal durability | ✅ PASS | `weak=False` on all signal connections; prevents GC disconnection |
| No pickle dependency | ✅ PASS | All data passed as plain dicts via Celery headers; JSON-compatible |
| Zero mandatory dependencies | ✅ PASS | Core library has no external dependencies; celery/json-logger are optional extras |
| Log record safety | ✅ PASS | `setattr()` guarded by `not hasattr()` check (no overwriting) and `_`-prefix rejection |

---

## Findings Summary

### SEC-ET-001 (MEDIUM): PII leakage risk via `bind_context()` extra dict
- **Status:** MITIGATED
- **Finding:** `bind_context()` accepts arbitrary key-value pairs in `extra` dict. `TraceContextFilter.filter()` injects all `extra` items into log records via `setattr()`. If consumers bind PII (email, IP, etc.), it appears in all subsequent log output.
- **Mitigation:** Logging filter now rejects keys starting with `_`. Consumers should still avoid binding sensitive data.
- **Implementation:** `expardus_tracing/logging.py` — `TraceContextFilter.filter()` skips extra keys starting with `_` when setting attributes on log records.
- **Tests:** `tests/test_logging.py::TestTraceContextFilter::test_filter_rejects_underscore_prefixed_extra_keys`

### SEC-ET-002 (LOW): Tracestate parser accepted dunder keys
- **Status:** FIXED
- **Finding:** `parse_tracestate()` accepted keys starting with `_`, including `__class__` and `__dict__`. While `setattr()` on LogRecord doesn't enable code execution, this violated defense-in-depth.
- **Implementation:** `expardus_tracing/w3c.py` — Keys starting with `_` are now rejected.
- **Tests:** `tests/test_w3c.py::TestParseTracestate::test_dunder_keys_rejected`, `test_underscore_prefix_keys_rejected`

### SEC-ET-003 (INFO): Tracestate parser had no size limits
- **Status:** FIXED
- **Finding:** No limits on member count, key length, or value length. Malicious tracestate headers could be arbitrarily large.
- **Implementation:** `expardus_tracing/w3c.py` — Max 32 members (per W3C spec), max 256 chars per key/value.
- **Tests:**
  - `tests/test_w3c.py::TestParseTracestate::test_max_32_members`
  - `test_key_length_limit`
  - `test_value_length_limit`

---

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

---

## Test Suite

Run: `python -m pytest tests/ -v`

### Security-Relevant Test Coverage

| Test File | Tests | Coverage Area |
|-----------|-------|---------------|
| `test_w3c.py::TestParseTraceparent` | 10 | Valid/invalid traceparent parsing, edge cases, normalization |
| `test_w3c.py::TestParseTraceparentFull` | 8 | Sampled flag parsing, roundtrips |
| `test_w3c.py::TestParseTracestate` | 11 | Key filtering, dunder rejection, size limits, edge cases |
| `test_w3c.py::TestFormatTracestate` | 4 | Formatting and roundtrip validation |
| `test_logging.py::TestTraceContextFilter` | 6 | Context injection, dunder key rejection, no-overwrite guard |
| `test_context.py` | * | Context lifecycle, bind_context, clear_trace_context |
| `test_celery_signals.py` | * | Signal registration, context propagation, cleanup |
| `test_concurrency.py` | * | Thread/async context isolation |

### Tests Added This Audit

| Test | Finding | What It Verifies |
|------|---------|------------------|
| `test_dunder_keys_rejected` | SEC-ET-002 | `parse_tracestate()` rejects `__class__`, `__dict__` |
| `test_underscore_prefix_keys_rejected` | SEC-ET-002 | `parse_tracestate()` rejects `_private` style keys |
| `test_max_32_members` | SEC-ET-003 | `parse_tracestate()` accepts at most 32 members |
| `test_key_length_limit` | SEC-ET-003 | `parse_tracestate()` rejects keys >256 chars |
| `test_value_length_limit` | SEC-ET-003 | `parse_tracestate()` rejects values >256 chars |
| `test_filter_rejects_underscore_prefixed_extra_keys` | SEC-ET-001 | `TraceContextFilter` doesn't inject `_`-prefixed extra keys into log records |

---

## Remediation Roadmap

### Now (Completed)
- [x] SEC-ET-002: Reject dunder/underscore-prefixed tracestate keys — **DONE**
- [x] SEC-ET-003: Add tracestate member count and length limits — **DONE**
- [x] SEC-ET-001: Filter underscore-prefixed keys in logging filter — **DONE**

### Future (Backlog)
- [ ] SEC-ET-001 (enhancement): Add `SENSITIVE_KEYS` deny-list or allow-list mechanism to `bind_context()` for consumers who need guardrails against PII in logs
- [ ] Consider adding tracestate key format validation (W3C spec: `lcalpha *(lcalpha / DIGIT / "_" / "-" / "*" / "/")`)
