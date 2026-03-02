# expardus-tracing: Medium & Strategic Improvements

> Exported from architecture breakdown (2026-03-02).  
> **Status:** M1–M6 implemented previously. **S1–S5 implemented (2026-03-02).**  
> See `docs/refactor/strategic-improvements/PARITY_MAP.md` for full checklist.

---

## Medium Changes

### M1: Add Idempotency Guard to `setup_celery_tracing`

**Problem:**  
`setup_celery_tracing(app)` can be called multiple times (e.g., in tests, or if a consumer accidentally registers twice). Each call adds duplicate signal handlers via `@signal.connect(weak=False)`, causing every signal to fire multiple times per task. This doubles logging output, duplicates OTel spans, and corrupts the `_active_spans` dict.

**Proposed Change:**  
Add a module-level `_initialized` flag inside `celery.py`. On re-call, log a warning and return early.

```python
# celery.py — top of module
_celery_tracing_initialized = False

def setup_celery_tracing(app: Any) -> None:
    global _celery_tracing_initialized
    if _celery_tracing_initialized:
        logging.getLogger("celery.tracing").warning(
            "setup_celery_tracing() called more than once — skipping"
        )
        return
    _celery_tracing_initialized = True
    # ... rest of function
```

**Risk:** Low. Only affects repeated calls. Existing single-call consumers are unaffected.

**Verification:**
- Add test: call `setup_celery_tracing` twice, assert signal receiver count didn't double.
- Add test: verify warning is logged on second call.

**Rollback:** Remove the flag and the guard; function reverts to current behavior.

---

### M2: Add `clear_trace_context()` to `task_failure` Handler

**Problem:**  
The `task_postrun` handler calls `clear_trace_context()` after a task completes, but the `task_failure` handler does not. In Celery's eager mode, `task_postrun` still fires after failure, so this isn't always a problem. However, in production with a real broker, if `task_postrun` doesn't fire (e.g., worker crash mid-task), the trace context leaks into the next task on the same thread/greenlet.

**Proposed Change:**  
Add `clear_trace_context()` at the end of `task_failure_handler` in `celery.py`:

```python
@task_failure.connect(weak=False)
def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, **kwargs):
    # ... existing logging ...
    clear_trace_context()  # ← add this
```

**Risk:** Low. Even if `task_postrun` also fires and calls `clear_trace_context()`, clearing an already-cleared context is a no-op (`_trace_context.set(None)`).

**Verification:**
- Add test: trigger task_failure signal, assert `get_trace_context() is None` after handler runs.
- Run `python -m pytest tests/test_celery_signals.py -v`.

**Rollback:** Remove the added line — reverts to current behavior.

---

### M3: Add Async/Threading Isolation Tests

**Problem:**  
The core value proposition of using `ContextVar` is safe isolation across async tasks and threads. Zero tests verify this. If a future change broke isolation, it could leak trace IDs across unrelated requests — a serious observability corruption.

**Proposed Change:**  
Create `tests/test_concurrency.py` with:

1. **Async test**: Run 10 concurrent `asyncio.gather` tasks, each setting a unique trace ID. Assert no cross-contamination.
2. **Threading test**: Run 10 concurrent `ThreadPoolExecutor` workers, each setting a unique trace ID. Assert no cross-contamination.
3. **Async scope test**: Verify `trace_context_scope` restores correctly across `await` boundaries.

```python
# tests/test_concurrency.py (sketch)
import asyncio
from concurrent.futures import ThreadPoolExecutor
from expardus_tracing import set_trace_context, get_trace_id, clear_trace_context

class TestAsyncIsolation:
    @pytest.mark.asyncio
    async def test_concurrent_tasks_isolated(self):
        results = {}
        async def worker(i):
            tid = f"{i:032x}"
            set_trace_context(trace_id=tid)
            await asyncio.sleep(0.01)  # yield control
            results[i] = get_trace_id()
            clear_trace_context()
        await asyncio.gather(*(worker(i) for i in range(10)))
        for i in range(10):
            assert results[i] == f"{i:032x}"

class TestThreadIsolation:
    def test_threads_isolated(self):
        results = {}
        def worker(i):
            tid = f"{i:032x}"
            set_trace_context(trace_id=tid)
            import time; time.sleep(0.01)
            results[i] = get_trace_id()
            clear_trace_context()
        with ThreadPoolExecutor(max_workers=5) as pool:
            list(pool.map(worker, range(10)))
        for i in range(10):
            assert results[i] == f"{i:032x}"
```

**Risk:** Low. Test-only change — no production code modified.

**Verification:** `python -m pytest tests/test_concurrency.py -v`

**Dependencies:** Requires `pytest-asyncio` (already present in dev environment based on test output).

**Rollback:** Delete the test file.

---

### M4: Migrate API Repo to Use Shared Package

**Problem:**  
`expardus_api/django_app/apps/common/tracing.py` (556 lines) is a full standalone copy of the tracing logic. It duplicates everything the shared package provides, plus two API-specific extras:
- `parse_traceparent_full()` — returns `(trace_id, span_id, sampled)` tuple
- `_is_valid_trace_id()` — private helper (already exists in shared package)

The API already has `expardus-tracing` in its `requirements.txt` but doesn't import from it. Any bug fix or improvement to the shared package doesn't reach the API.

**Proposed Change:**  
Convert `apps/common/tracing.py` to a thin wrapper (same pattern as bot/workers):
1. Import and re-export all 37 symbols from `expardus_tracing`.
2. Keep `parse_traceparent_full()` as a local API-specific function.
3. Remove all duplicated implementations.
4. Verify `apps/common/middleware/tracing.py` (`RequestTracingMiddleware`) still works — it imports from `apps.common.tracing`, so the re-exports maintain compatibility.

**Risk:** Medium. The API is the most critical service. Requires careful testing.

**Verification:**
1. `cd django_app && python -m pytest tests/ -v`
2. `cd django_app && python -m pytest tests/test_tracing.py -v` (dedicated tracing tests)
3. Manual smoke test: verify `traceparent` header appears in API responses.

**Rollback:** Restore the standalone `tracing.py` from git history.

---

### M5: Update Parity Map Checklist

**Problem:**  
`docs/refactor/extract-expardus-tracing/PARITY_MAP.md` has all items marked ☐ (unchecked) despite the refactor being complete for 4 of 5 consumers.

**Proposed Change:**  
Mark all implemented items as ☑. Mark the API migration (M4) as ☐ remaining.

**Risk:** None — documentation only.

**Verification:** Visual review of the file.

---

### M6: Add TTL/Max-Size Guard to `_active_spans` Dict

**Problem:**  
In `celery.py`, the `_active_spans` dict stores OTel spans keyed by `task_id`. If a task crashes hard enough that neither `task_postrun` nor `task_failure` fires, the entry is never removed. Over time in a long-running worker, this can leak memory.

**Proposed Change:**  
Use an `OrderedDict` with a max size (e.g., 10,000 entries). When inserting a new entry and the dict exceeds max size, pop the oldest entry (likely a leaked orphan).

```python
from collections import OrderedDict

_active_spans: OrderedDict[str, Any] = OrderedDict()
_MAX_ACTIVE_SPANS = 10_000

# In task_prerun_handler, after inserting:
if len(_active_spans) > _MAX_ACTIVE_SPANS:
    orphan_id, orphan_span = _active_spans.popitem(last=False)
    _logger.warning("Evicted orphan span", extra={"task_id": orphan_id})
```

**Risk:** Low. Only triggers if >10k tasks are simultaneously in-flight without completing, which indicates a deeper problem.

**Verification:**
- Unit test: insert 10,001 mock entries, assert oldest is evicted.
- Run existing Celery test suite.

**Rollback:** Revert to plain `dict`.

---

## Strategic Upgrades

### S1: Replace Local File Path Install with Git+SSH URL

**Problem:**  
All 5 consumers reference the package as:
```
expardus-tracing @ file:///C:\Users\Techn/OneDrive/Desktop/exPardus/expardus_tracing
```
This is a local filesystem path that only works on the developer's machine. CI/CD pipelines and other developers cannot install the package.

**Proposed Change:**  
Replace the local path with a Git+SSH reference in all `requirements.txt`:
```
expardus-tracing @ git+ssh://git@github.com/exPardus/expardus_tracing.git@v0.1.0
```
Or for HTTPS:
```
expardus-tracing @ git+https://github.com/exPardus/expardus_tracing.git@v0.1.0
```
Pin to git tags (e.g., `@v0.1.0`) rather than branch names.

**Risk:** Medium. Requires:
- The repo being accessible from CI runners (SSH keys or deploy tokens).
- All 5 consumer repos updated simultaneously or in a coordinated rollout.
- Developers running `pip install -e` locally for development with editable installs.

**Verification:**
1. `pip install "expardus-tracing @ git+https://..."` succeeds in a clean venv.
2. All consumer test suites pass with the new requirement reference.
3. Render deployment succeeds with the Git URL (may need deploy key).

**Rollback:** Revert `requirements.txt` to local file path.

**Alternative:** If private PyPI hosting is available (e.g., GitHub Packages, AWS CodeArtifact), publish there instead for faster installs and proper version resolution.

---

### S2: Add `py.typed` Marker + Type Checking

**Problem:**  
The package has comprehensive type hints throughout (return types, parameter types, `X | Y` unions), but no PEP 561 `py.typed` marker file. This means type checkers like mypy and pyright in consumer repos treat the package as untyped, losing all the type safety benefits.

**Proposed Change:**
1. Create `expardus_tracing/py.typed` (empty marker file).
2. Add `[tool.mypy]` section to `pyproject.toml` with strict settings.
3. Run `mypy expardus_tracing/` and fix any issues.
4. Add mypy check to CI/test workflow.

```toml
# pyproject.toml additions
[tool.mypy]
python_version = "3.10"
strict = true
warn_return_any = true
warn_unused_configs = true
```

**Risk:** Low. The marker file is additive — consumers that don't use type checkers are unaffected.

**Verification:**
- `mypy expardus_tracing/ --strict` passes.
- `pyright expardus_tracing/` passes.
- Consumer type checkers resolve library types.

**Rollback:** Delete `py.typed` and remove the mypy config section.

---

### S3: Add `tracestate` Support (W3C Companion Header)

**Problem:**  
The W3C Trace Context specification includes two headers: `traceparent` (implemented) and `tracestate` (not implemented). `tracestate` carries vendor-specific trace context (e.g., sampling decisions, feature flags, routing hints). Without it, the implementation is partially W3C-compliant.

**Proposed Change:**
1. Add `parse_tracestate()` and `format_tracestate()` to `w3c.py`.
2. Add a `tracestate: dict[str, str]` field to `TraceContext` (default empty).
3. Update `extract_trace_from_headers()` to also extract `tracestate`.
4. Update `get_trace_headers()` to include `tracestate` when present.

```python
# w3c.py
def parse_tracestate(header: str | None) -> dict[str, str]:
    """Parse W3C tracestate header into key-value pairs."""
    if not header:
        return {}
    result = {}
    for member in header.split(","):
        member = member.strip()
        if "=" in member:
            key, value = member.split("=", 1)
            result[key.strip()] = value.strip()
    return result

def format_tracestate(state: dict[str, str]) -> str:
    """Format tracestate dict into header value."""
    return ",".join(f"{k}={v}" for k, v in state.items())
```

**Risk:** Low. Additive change — existing behavior unchanged when `tracestate` header is absent.

**Verification:**
- Unit tests for parse/format roundtrip.
- Integration test verifying tracestate survives HTTP and Celery propagation.

**Rollback:** Remove the new functions and the `tracestate` field.

---

### S4: Add Sampling Decision Propagation

**Problem:**  
`parse_traceparent()` currently discards the `flags` field (4th segment of the traceparent header). The `sampled` flag (`01` = sampled, `00` = not sampled) is important for:
- Reducing trace volume in high-throughput services.
- Honoring upstream sampling decisions (head-based sampling).
- Compatibility with OTel collectors that respect the sampled flag.

The API repo's standalone `parse_traceparent_full()` already extracts this flag, but the shared package does not.

**Proposed Change:**
1. Add `sampled: bool = True` field to `TraceContext`.
2. Add `parse_traceparent_full()` to `w3c.py` (returns `(trace_id, span_id, sampled)` tuple).
3. Update `format_traceparent()` to accept `sampled` from context when not explicitly passed.
4. Preserve the existing `parse_traceparent()` API unchanged for backward compatibility.

**Risk:** Medium. Consumers that destructure `parse_traceparent()` return values are unaffected (it still returns 2-tuple). But adding `sampled` to `TraceContext` changes the dataclass shape — any code that constructs `TraceContext` positionally (unlikely but possible) would break.

**Verification:**
- All existing tests pass unchanged.
- New tests: parse sampled/unsampled flags, roundtrip, default behavior.
- Run all consumer test suites.

**Rollback:** Remove the `sampled` field and `parse_traceparent_full`.

---

### S5: Add `@traced()` Decorator API

**Problem:**  
Currently, tracing a function requires wrapping the body in a `with trace_span(...)` context manager:

```python
def process_order(order_id):
    with trace_span("process_order", order_id=order_id) as span:
        # ... function body ...
```

This adds nesting and is easy to forget.

**Proposed Change:**  
Add a `@traced("operation_name")` decorator that wraps the function in `trace_span`:

```python
# context.py
import functools

def traced(operation: str, **static_extra):
    """Decorator that wraps a function in a trace_span."""
    def decorator(func):
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            with trace_span(operation, **static_extra):
                return func(*args, **kwargs)
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            with trace_span(operation, **static_extra):
                return await func(*args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator
```

Usage:
```python
@traced("process_order")
def process_order(order_id):
    # ... function body — automatically spans
```

**Risk:** Low. Purely additive — new public API, no changes to existing code.

**Verification:**
- Unit tests for sync and async decorated functions.
- Test that trace_id is preserved and span_id changes.
- Test nested decorated functions.

**Rollback:** Remove the decorator function and its `__all__` entry.
