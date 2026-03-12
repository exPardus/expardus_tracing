# Optimization Audit — expardus_tracing

**Date**: 2026-03-13
**Baseline**: 134 tests passing (0.72s), zero lint errors

## Repo Structure

| Module | Lines | Role |
|--------|-------|------|
| `context.py` | ~270 | Core TraceContext, ContextVar, scoped helpers, decorator |
| `w3c.py` | ~140 | W3C traceparent/tracestate parse/format |
| `headers.py` | ~185 | HTTP & Celery header extraction/injection |
| `logging.py` | ~90 | TraceContextFilter, setup_logging |
| `celery.py` | ~230 | Celery signal handlers for trace propagation |
| `__init__.py` | ~145 | Public API re-exports, config constants |

## Findings

### Fixed

1. **Duplicated parsing logic in w3c.py** — `parse_traceparent` and `parse_traceparent_full` had identical validation code. Refactored `parse_traceparent` to delegate to `parse_traceparent_full`.

2. **Slow hex validation** — Character-by-character `all(c in ".." for c in s)` replaced with `int(s, 16)` try/except in both `w3c.py` and `headers.py`. Faster for valid input, equivalent for invalid.

3. **Unused variable** — `_service_name` in `logging.py` was defined but never referenced. Removed.

### No Action Needed

- Code is well-structured with clear separation of concerns
- Test coverage is comprehensive (134 tests across 8 test files)
- Public API surface is well-defined via `__all__`
- Type hints are used throughout
- No dead code beyond the removed `_service_name`
