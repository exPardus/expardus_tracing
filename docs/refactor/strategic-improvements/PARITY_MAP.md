# Parity Map: Strategic Improvements (S1–S5)

> Source: `docs/architecture/medium_and_strategic_improvements.md`
> Date: 2026-03-02

## Acceptance Criteria Checklist

### S1: Replace Local File Path Install with Git+SSH URL
- [x] All 5 consumer `requirements.txt` use `git+https://` URL instead of `file:///` path
- [x] Pin to a git tag (`@v0.1.0`)
- [ ] `pip install` from the URL succeeds in a clean venv (requires git push + tag)
- [ ] All consumer test suites pass with the new reference (requires deploy)

### S2: Add `py.typed` Marker + Type Checking
- [x] `expardus_tracing/py.typed` marker file exists (empty)
- [x] `[tool.mypy]` section added to `pyproject.toml` with strict settings
- [x] `mypy expardus_tracing/ --strict` passes cleanly (0 issues)
- [x] Existing tests still pass (96/96)

### S3: Add `tracestate` Support (W3C Companion Header)
- [x] `parse_tracestate()` function in `w3c.py`
- [x] `format_tracestate()` function in `w3c.py`
- [x] `tracestate: dict[str, str]` field on `TraceContext` (default empty)
- [x] `extract_trace_from_headers()` extracts `tracestate` when present
- [x] `get_trace_headers()` includes `tracestate` when present
- [x] Round-trip tests for parse/format (12 new tests)
- [x] Backward compatible — absent tracestate = no behavior change
- [x] Re-exported from `__init__.py` and in `__all__`

### S4: Add Sampling Decision Propagation
- [x] `sampled: bool = True` field on `TraceContext`
- [x] `parse_traceparent_full()` in `w3c.py` returns `(trace_id, span_id, sampled)` 3-tuple
- [x] `format_traceparent()` uses `sampled` from context when not explicitly passed
- [x] Existing `parse_traceparent()` remains unchanged (2-tuple)
- [x] All existing tests pass unchanged
- [x] New tests for sampled/unsampled flags and round-trip (13 new tests)
- [x] Re-exported from `__init__.py` and in `__all__`

### S5: Add `@traced()` Decorator API
- [x] `traced(operation, **static_extra)` decorator in `context.py`
- [x] Supports sync functions
- [x] Supports async functions
- [x] Preserves trace_id, creates new span_id
- [x] Nested decorators work correctly
- [x] Re-exported from `__init__.py` and in `__all__`
- [x] Unit tests for sync, async, nested (8 new tests)

## High-Risk Areas

| Area | Risk | Mitigation |
|------|------|------------|
| S3/S4: `TraceContext` dataclass shape change | Medium | New fields have defaults, positional construction unlikely |
| S4: `format_traceparent` behavior | Low | Default `sampled=True` preserves current behavior |
| S1: All consumers must update simultaneously | Medium | Coordinate rollout, verify in clean venv |
| S5: Async detection edge cases | Low | Use `asyncio.iscoroutinefunction()` |

## Behavior Invariants (Must NOT Change)

1. `parse_traceparent()` returns 2-tuple `(trace_id, span_id)` — unchanged
2. `format_traceparent(tid, sid)` produces valid W3C traceparent — unchanged
3. `TraceContext(trace_id=..., span_id=...)` works with keyword args — unchanged
4. All existing `__all__` symbols remain importable
5. `clear_trace_context()` is safe to call multiple times
6. ContextVar isolation across threads/async tasks — unchanged
