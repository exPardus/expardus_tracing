# Architecture Breakdown: `expardus-tracing` Package

## 1. Scope

### Analyzed
- All 5 source modules: `context.py`, `w3c.py`, `headers.py`, `logging.py`, `celery.py`
- Package init and public API: `__init__.py`
- Full test suite: 6 test files, 81 tests
- All 5 consumer repos/wrappers
- Package metadata: `pyproject.toml`, egg-info
- Refactor planning docs: `docs/refactor/extract-expardus-tracing/`

### Intentionally Ignored
- Worker-specific `otel_worker.py` files (OTel bridge — separate concern)
- Django API middleware (`RequestTracingMiddleware`) — consumer-side integration
- Bot-specific OTel init (`init_otel_bot`) — consumer-side extension
- Frontend repo (no Python, no tracing dependency)

---

## 2. System Map

### Package Modules

| Module | Lines | Role |
|--------|------:|------|
| `__init__.py` | 140 | Re-exports all public symbols, defines `SERVICE_NAME`/`ENV`/`RELEASE` config |
| `context.py` | 203 | Core: `TraceContext` dataclass, `ContextVar` storage, ID generation, scoped helpers |
| `w3c.py` | 57 | W3C `traceparent` header parsing and formatting |
| `headers.py` | 179 | HTTP + Celery header extraction/injection, header constants |
| `logging.py` | 90 | `TraceContextFilter` for stdlib logging, `setup_logging()` for workers |
| `celery.py` | 157 | `setup_celery_tracing()` — Celery signal handlers for automatic propagation |

### Test Files

| File | Tests | Coverage Target |
|------|------:|-----------------|
| `test_context.py` | 20 | ID generation, context CRUD, bind/scope/span |
| `test_w3c.py` | 15 | parse/format roundtrips, edge cases |
| `test_headers.py` | 20 | HTTP+Celery extract/inject, constants |
| `test_logging.py` | 7 | Filter injection, setup_logging |
| `test_celery_signals.py` | 6 | Signal registration, prerun/postrun handlers |
| `test_celery_integration.py` | 13 | End-to-end Celery trace propagation lifecycle |

### Consumer Map

| Consumer | File | Strategy |
|----------|------|----------|
| `celery/bot_worker` | `tracing.py` (51 lines) | Pure re-export shim |
| `celery/general_worker` | `tracing.py` (60 lines) | Pure re-export shim |
| `celery/media_worker` | `tracing.py` (60 lines) | Pure re-export shim |
| `expardus_telegram_bot` | `app/tracing.py` (229 lines) | Re-export + 7 bot-specific symbols |
| `expardus_api` | `apps/common/tracing.py` (556 lines) | **NOT migrated** — standalone duplicate |

---

## 3. Data Flow & Control Flow

### 3.1 Core Execution Narrative

#### How trace context is established
1. A request/task arrives at a service boundary (HTTP request or Celery task message).
2. The service extracts trace identifiers from inbound headers:
   - **HTTP**: `extract_trace_from_headers()` checks `traceparent` → `x-trace-id` → `x-request-id` (priority order).
   - **Celery**: `extract_trace_from_celery_headers()` checks `traceparent` → `trace_id`/`parent_span_id` keys.
3. `set_trace_context()` stores a `TraceContext` in a `ContextVar` — safe for async and threading.
4. If no inbound trace ID exists, `generate_trace_id()` creates a new 32-char hex ID (128-bit, W3C-compatible).

#### How trace context propagates to outbound calls
1. Before making an HTTP call: `get_trace_headers()` returns `{"x-trace-id": ..., "traceparent": ...}`.
2. Before dispatching a Celery task: `get_celery_trace_headers()` returns `{"trace_id": ..., "parent_span_id": ..., "traceparent": ...}`.
3. The Celery integration (`setup_celery_tracing`) automates this via `before_task_publish` signal.

#### How logging integrates
1. `TraceContextFilter` is added to log handlers.
2. On every log record, it injects `trace_id`, `span_id`, `parent_span_id`, `service`, `env`, `release`.
3. `setup_logging()` configures root logger with JSON formatting + the filter.

#### How cleanup happens
1. `task_postrun` signal handler calls `clear_trace_context()`.
2. `trace_context_scope()` and `trace_span()` context managers auto-restore on exit.

### 3.2 Celery Lifecycle (Automated via Signals)

```
Producer                    Broker                   Worker
   │                          │                        │
   │ set_trace_context()      │                        │
   │ task.delay()             │                        │
   │───before_task_publish────│                        │
   │  (inject headers)       │                        │
   │                          │───deliver message──────│
   │                          │                        │
   │                          │                task_prerun
   │                          │         (extract headers, set context)
   │                          │                        │
   │                          │              [task executes]
   │                          │         (logging has trace_id)
   │                          │         (sub-tasks get headers)
   │                          │                        │
   │                          │               task_postrun
   │                          │         (log latency, clear context)
   │                          │                        │
   │                          │    [on failure: task_failure]
   │                          │    [on retry: task_retry]
```

### 3.3 Span Hierarchy

```
trace_context_scope (root)
  └── trace_span("operation_a")
       ├── trace_id = parent.trace_id (preserved)
       ├── span_id = new generated
       ├── parent_span_id = parent.span_id
       └── trace_span("operation_b")
            ├── trace_id = same (preserved)
            ├── span_id = new generated
            └── parent_span_id = operation_a.span_id
```

---

## 4. Key Contracts & Invariants

- **Trace ID format**: Always 32 lowercase hex characters (128-bit, W3C Trace Context spec).
- **Span ID format**: Always 16 lowercase hex characters (64-bit, W3C spec).
- **Traceparent format**: `00-{trace_id}-{span_id}-{flags}` (version 00 only).
- **All-zero trace IDs rejected**: `parse_traceparent` returns `(None, None)` for `0x0...0` trace IDs.
- **ContextVar isolation**: `TraceContext` lives in `ContextVar` — safe for concurrent tasks, asyncio, and threads.
- **Celery signals use `weak=False`**: Inner closures would be GC'd otherwise, silently breaking tracing.
- **ID generation uses `secrets.token_hex`**: Cryptographically random, not `uuid4`.
- **Header extraction is case-insensitive**: HTTP headers are normalised to lowercase before lookup.
- **`setup_celery_tracing()` is call-once**: Signals should be registered exactly once per Celery app instance.
- **No required dependencies**: Core package has zero deps; Celery and JSON logging are optional extras.
- **Graceful OTel degradation**: If `otel_worker` module is not on `sys.path`, Celery tracing works without it.

---

## 5. Failure Modes & Observability

### Known Failure Modes

| Mode | Impact | Current Handling |
|------|--------|-----------------|
| Missing/invalid traceparent header | Trace chain broken | New trace ID generated (graceful) |
| Celery `weak=True` GC | All signal handlers silently lost | Fixed via `weak=False` |
| `otel_worker` ImportError | No OTel spans/metrics | `try/except ImportError` — logs still work |
| `python-json-logger` not installed | No JSON log output | Falls back to text formatter |
| `setup_celery_tracing` called multiple times | Duplicate signal handlers | No guard — signals fire twice |
| Context not cleared after exception | Leaked context in subsequent requests | `task_postrun` only fires on success/fail; manual `clear_trace_context()` needed in some paths |
| `task_failure` handler accesses `ctx.start_time` when `ctx is None` | AttributeError | Guarded with `if ctx else 0` |

### Observability

- Celery signal handlers emit structured log events: `task_start`, `task_complete`, `task_failure`, `task_retry`.
- Each event includes `trace_id`, `task_id`, `task_name`, `latency_ms`.
- `TraceContextFilter` injects trace context into every log record across the application.
- No built-in metrics/counters beyond OTel bridge passthrough.

---

## 6. Test Coverage Reality Check

### What's covered (81 tests, all passing)

| Area | Tests | Key Assertions |
|------|------:|----------------|
| ID generation | 6 | Length, hex validity, uniqueness (200 samples) |
| Context CRUD | 7 | Set/get/clear, auto-generation, extra fields |
| `bind_context` | 4 | Add/restore fields, no-op without context |
| `trace_context_scope` | 3 | Create/restore/extra |
| `trace_span` | 3 | Trace ID preserved, parent linking, nesting |
| W3C parse | 11 | Valid, invalid, edge cases, roundtrip |
| W3C format | 4 | Sampled/unsampled flags, roundtrip |
| HTTP header extract | 8 | Priority order, case insensitivity, validation |
| Celery header extract | 5 | traceparent, simple keys, alias |
| HTTP header inject | 3 | No-context empty, with-context populated |
| Celery header inject | 5 | Keys, values, roundtrip, alias |
| Logging filter | 5 | With/without context, service info, extras |
| `setup_logging` | 1 | Root handler configured |
| Celery signals | 6 | Registration, inject, prerun, postrun |
| Celery integration | 8 | End-to-end propagation, subtask, clearing, traceparent roundtrip |

### What's missing (gaps ranked by risk)

| Gap | Risk | Why |
|-----|------|-----|
| **`trace_span` operation param unused** | Medium | `operation` is accepted but never stored in `TraceContext.extra` — misleading API |
| **`get_http_trace_headers` header-casing inconsistency** | High | Uses `"X-Trace-ID"` while `get_trace_headers` uses `"x-trace-id"` — untested, could cause double-header bugs |
| **`setup_celery_tracing` called twice** | Medium | No idempotency guard — duplicate signal handlers fire |
| **`setup_logging` JSON fallback deprecation** | Low | `pythonjsonlogger.jsonlogger` import path deprecated; test passes but warns |
| **Async/threading isolation** | Medium | No tests for `ContextVar` behavior under `asyncio.gather` or thread pools |
| **`task_failure` context access when None** | Low | Guarded but no test verifies the guard |
| **`clear_trace_context` not called on task_failure** | Medium | Failure handler logs but doesn't clear; potential context leakage |
| **`__all__` vs actual exports** | Low | No test asserting `__all__` matches real exports |
| **No `README.md`** | High | Package has no README; `pyproject.toml` references it but it doesn't exist |
| **Version `0.2.0` in pyproject but no tags** | Medium | No semver tagging; no changelog |

---

## 7. Improvement Ideas (Ranked)

### Quick Wins (Low Effort, High Confidence)

| # | Problem | Proposal | Risk | Verification |
|---|---------|----------|------|--------------|
| Q1 | No `README.md` — pyproject.toml references it | Create `README.md` with quick start, API reference, install instructions | None | `python -m build` succeeds |
| Q2 | `trace_span` ignores `operation` param | Store `operation` in `ctx.extra["operation"]` | None | Add unit test |
| Q3 | `get_http_trace_headers` uses `"X-Trace-ID"` vs `"x-trace-id"` | Unify both functions to use the `TRACE_ID_HEADER` constant | Low | Existing tests + add case-specific test |
| Q4 | pyproject.toml says `0.2.0` but user wants `0.1.0` release | Set version to `0.1.0`, add `CHANGELOG.md` | None | Visual |
| Q5 | `pythonjsonlogger.jsonlogger` import deprecated | Update import to `pythonjsonlogger.json.JsonFormatter` with fallback | None | Warning disappears in test run |
| Q6 | Missing `.env.example` / env var docs | Document `SERVICE_NAME`, `ENV`, `RELEASE`, `LOG_JSON_ENABLED`, `LOG_LEVEL` in README | None | Visual |
| Q7 | `__all__` completeness untested | Add `test___all___matches_exports` test | None | Test |

### Medium Changes (Some Refactor or New Tests)

| # | Problem | Proposal | Risk | Verification |
|---|---------|----------|------|--------------|
| M1 | No idempotency guard on `setup_celery_tracing` | Add a module-level `_initialized` flag; log warning on re-call | Low | Add test calling setup twice |
| M2 | `task_failure` doesn't call `clear_trace_context` | Add `clear_trace_context()` at end of failure handler | Low | Add test |
| M3 | No async/threading tests | Add tests with `asyncio.gather` and `concurrent.futures.ThreadPoolExecutor` | Low | New test file |
| M4 | API repo (556-line standalone) not migrated | Convert `apps/common/tracing.py` to thin wrapper + API-specific extras (`parse_traceparent_full`) | Medium | Run API test suite |
| M5 | Parity map checklist items all unchecked | Update `docs/refactor/PARITY_MAP.md` with ☑ for completed items | None | Visual |
| M6 | `celery.py` OTel bridge uses module-level `_active_spans` dict | Could leak entries if task_id never reaches postrun (crash). Add TTL or max-size guard | Low | Add test |

### Strategic Upgrades (Bigger Architecture Steps)

| # | Problem | Proposal | Risk | Verification |
|---|---------|----------|------|--------------|
| S1 | Package only installable via local file path | Publish to private PyPI or use Git+SSH URL in `requirements.txt` for CI/CD | Medium | All consumers install cleanly |
| S2 | No `py.typed` marker | Add `py.typed` + verify mypy/pyright passes on the package | Low | `mypy expardus_tracing/` |
| S3 | No tracestate support (W3C companion header) | Add `parse_tracestate` / `format_tracestate` in `w3c.py` | Low | Spec compliance |
| S4 | No sampling decision propagation | `parse_traceparent` discards `flags`; add `sampled` field to `TraceContext` | Medium | Backward compat needed |
| S5 | No decorator API for tracing functions | Add `@traced("operation_name")` decorator wrapping `trace_span` | Low | Ergonomic improvement |

---

## 8. Recommended Next Steps (v0.1.0 Release Checklist)

1. **Fix version**: Set `pyproject.toml` version to `0.1.0`.
2. **Create `README.md`**: Quick start, API overview, env vars, install instructions.
3. **Create `CHANGELOG.md`**: Document initial release.
4. **Fix `trace_span`**: Store `operation` parameter in context extra.
5. **Fix header casing inconsistency**: Unify `get_trace_headers` / `get_http_trace_headers` to use consistent header name constants.
6. **Fix `task_failure` handler**: Add `clear_trace_context()` call.
7. **Add `setup_celery_tracing` idempotency guard**.
8. **Fix `pythonjsonlogger` deprecation warning**.
9. **Add missing tests**: async isolation, `__all__` validation, double-setup guard.
10. **Tag `v0.1.0`** in git after all above are merged.

---

## Appendix: Full Public API (`__all__`)

```
# Config
SERVICE_NAME, ENV, RELEASE

# Context
TraceContext, generate_trace_id, generate_span_id
get_trace_context, set_trace_context, clear_trace_context
get_trace_id, get_span_id, get_elapsed_ms, set_trace_id
bind_context, trace_context_scope, trace_span

# W3C
parse_traceparent, format_traceparent

# Headers
extract_trace_from_headers, extract_trace_from_celery_headers
extract_trace_from_task_headers
get_trace_headers, get_http_trace_headers
get_celery_trace_headers, get_trace_headers_for_task
TRACEPARENT_HEADER, TRACE_ID_HEADER, REQUEST_ID_HEADER
CELERY_TRACE_ID_KEY, CELERY_SPAN_ID_KEY, CELERY_TRACEPARENT_KEY

# Logging
TraceContextFilter, get_logger, setup_logging

# Celery
setup_celery_tracing
```
