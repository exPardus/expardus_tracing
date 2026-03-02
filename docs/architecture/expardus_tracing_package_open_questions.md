# Open Questions: `expardus-tracing` v0.1.0 Readiness

## Confirmed Issues (Action Required)

### OQ-1: Version number mismatch
- **Status**: `pyproject.toml` says `0.2.0`, but the package has never been formally released.
- **Evidence**: Only 2 git commits, zero tags.
- **Question**: Should v0.1.0 be the first release, or honor the 0.2.0 already in pyproject?
- **How to confirm**: Decision from maintainer.

### OQ-2: API repo not migrated
- **Status**: `expardus_api/django_app/apps/common/tracing.py` (556 lines) is a standalone duplicate.
- **Evidence**: File does not import `expardus_tracing` (confirmed via grep). It has `requirements.txt` pointing to the package but doesn't use it.
- **Question**: Is API migration a v0.1.0 blocker or a follow-up task?
- **How to confirm**: Run `grep -r "from expardus_tracing" expardus_api/` — returns nothing.

### OQ-3: `get_trace_headers` vs `get_http_trace_headers` — which is canonical?
- **Status**: Both exist with near-identical behavior but use different header name casing:
  - `get_trace_headers()` → `{"x-trace-id": ..., "traceparent": ...}`
  - `get_http_trace_headers()` → `{"X-Trace-ID": ..., "traceparent": ...}`
- **Evidence**: `headers.py` lines 88-112.
- **Question**: Should one be deprecated? Should both use the constant `TRACE_ID_HEADER = "x-trace-id"`?
- **How to confirm**: Check all consumer call-sites to see which casing their HTTP clients expect.

### OQ-4: Should `task_failure` clear trace context?
- **Status**: `task_postrun` calls `clear_trace_context()`, but `task_failure` does not.
- **Evidence**: `celery.py` lines 95-98 vs 115-136.
- **Question**: Is this intentional (to allow post-failure logging) or a bug?
- **How to confirm**: Check if `task_postrun` still fires after `task_failure` (Celery docs say it does for `task_always_eager` but may vary).

## Unconfirmed / Low Priority

### OQ-5: Is `trace_span` `operation` parameter intentionally ignored?
- **Status**: `trace_span("db_query")` accepts `operation` as first arg but never stores it.
- **Evidence**: `context.py` lines 172-203 — `operation` is only used for doc purposes.
- **How to confirm**: Check if any consumer relies on `ctx.extra["operation"]` being set.

### OQ-6: Should the package support Python 3.9?
- **Status**: Currently `requires-python = ">=3.10"`. All features use 3.10+ syntax (`X | Y` unions).
- **Evidence**: `pyproject.toml` line 10.
- **How to confirm**: Check Python version constraints in all consumer repos.

### OQ-7: Should `CELERY_SPAN_ID_KEY = "parent_span_id"` be renamed?
- **Status**: The key name is misleading — on the *producer* side it's the current span_id being sent as the *child's* parent. On the *consumer* side it's correctly the parent span ID.
- **Evidence**: `headers.py` line 31.
- **How to confirm**: Check if renaming would break existing Celery messages in flight (likely yes — don't rename for v0.1.0).

### OQ-8: No `py.typed` marker for type checker support
- **Status**: Package has type hints throughout but no PEP 561 `py.typed` marker file.
- **Evidence**: `ls expardus_tracing/py.typed` — does not exist.
- **How to confirm**: Try running `mypy` or `pyright` against a consumer to see if types resolve.
