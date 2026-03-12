# Security Audit Report - expardus_tracing

**Audit Date:** July 25, 2026
**Auditor:** GitHub Copilot Security Assessment
**Repository:** expardus_tracing
**Scope:** Full security assessment of the shared tracing library

---

## Executive Summary

### Overall Security Posture: **GOOD** ✅

`expardus_tracing` is a small shared library with zero mandatory dependencies and a minimal attack surface. It uses cryptographically secure random generation (`secrets.token_hex`), async-safe context propagation (`contextvars.ContextVar`), robust W3C traceparent parsing with fail-safe defaults, and proper Celery signal lifecycle management. No Critical or High findings.

**Findings:**

1. **SEC-ET-001** (MEDIUM): PII leakage risk via `bind_context()` extra dict — **MITIGATED** (logging filter now rejects underscore-prefixed keys)
2. **SEC-ET-002** (LOW): Tracestate parser accepted dunder keys — **FIXED**
3. **SEC-ET-003** (INFO): Tracestate parser had no size limits — **FIXED**

---

## Findings Table

| ID | Severity | Component | Finding | Status |
|----|----------|-----------|---------|--------|
| SEC-ET-001 | MEDIUM | context.py, logging.py | `bind_context()` accepts arbitrary key-value pairs in `extra` dict. `TraceContextFilter.filter()` injects all `extra` items into log records via `setattr()`. If consumers bind PII (email, IP, etc.), it appears in all subsequent log output. | **MITIGATED** — Logging filter now rejects keys starting with `_`. Consumers should still avoid binding sensitive data. |
| SEC-ET-002 | LOW | w3c.py `parse_tracestate()` | Accepted keys starting with `_`, including `__class__` and `__dict__`. While `setattr()` on LogRecord doesn't enable code execution, this violated defense-in-depth. | **FIXED** — Keys starting with `_` are now rejected. |
| SEC-ET-003 | INFO | w3c.py `parse_tracestate()` | No limits on member count, key length, or value length. Malicious tracestate headers could be arbitrarily large. | **FIXED** — Max 32 members (per W3C spec), max 256 chars per key/value. |

---

## Patch Summary

### SEC-ET-001: Logging Filter Key Safety (MITIGATED)

**File modified:** `expardus_tracing/logging.py`
- `TraceContextFilter.filter()` now skips extra keys starting with `_` when setting attributes on log records
- This prevents dunder key injection (`__class__`, `__dict__`) and discourages private attribute names

**Tests added:** `tests/test_logging.py::TestTraceContextFilter::test_filter_rejects_underscore_prefixed_extra_keys`

### SEC-ET-002 + SEC-ET-003: Tracestate Parser Hardening (FIXED)

**File modified:** `expardus_tracing/w3c.py`
- `parse_tracestate()` now rejects keys starting with `_`
- Maximum 32 members accepted (W3C Trace Context specification limit)
- Key and value length capped at 256 characters

**Tests added:**
- `tests/test_w3c.py::TestParseTracestate::test_dunder_keys_rejected`
- `tests/test_w3c.py::TestParseTracestate::test_underscore_prefix_keys_rejected`
- `tests/test_w3c.py::TestParseTracestate::test_max_32_members`
- `tests/test_w3c.py::TestParseTracestate::test_key_length_limit`
- `tests/test_w3c.py::TestParseTracestate::test_value_length_limit`

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

## Remediation Roadmap

### Now (This Sprint)
- [x] SEC-ET-002: Reject dunder/underscore-prefixed tracestate keys — **DONE**
- [x] SEC-ET-003: Add tracestate member count and length limits — **DONE**
- [x] SEC-ET-001: Filter underscore-prefixed keys in logging filter — **DONE**

### Next (Next Sprint)
- [ ] SEC-ET-001 (enhancement): Add `SENSITIVE_KEYS` deny-list or allow-list mechanism to `bind_context()` for consumers who need guardrails against PII in logs
- [x] Add documentation to README.md warning against binding PII via `bind_context()` — **DONE**

### Later (Backlog)
- [ ] Consider adding tracestate key format validation (W3C spec: `lcalpha *(lcalpha / DIGIT / "_" / "-" / "*" / "/")`)
