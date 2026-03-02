# Refactor Notes: Strategic Improvements

## Baseline State (2026-03-02)

- 96 tests all passing
- Package version: 0.1.0
- 6 source files in `expardus_tracing/`
- M1–M6 (medium improvements) already implemented
- 5 consumers use `file:///` local path install

## Key Code Locations

- `expardus_tracing/context.py` — TraceContext dataclass, context management, trace_span
- `expardus_tracing/w3c.py` — parse_traceparent, format_traceparent
- `expardus_tracing/headers.py` — HTTP/Celery header extraction/injection
- `expardus_tracing/celery.py` — Celery signal handlers
- `expardus_tracing/logging.py` — TraceContextFilter, setup_logging
- `expardus_tracing/__init__.py` — re-exports and __all__

## Decisions Log

| Decision | Rationale |
|----------|-----------|
| Add `tracestate` as `dict[str, str]` field with `field(default_factory=dict)` | Mutable default needs factory; dict is simplest representation |
| Keep `parse_traceparent()` unchanged (2-tuple) | Backward compat; add `parse_traceparent_full()` for 3-tuple |
| `sampled` defaults to `True` | Matches W3C convention — default is sampling enabled |
| `traced()` uses `asyncio.iscoroutinefunction()` | Standard detection; handles regular async functions correctly |
| S1 done last | Changing install paths affects all consumers; do after all code changes are stable |

## Verified

- [x] S2 implemented and tested (96 tests, mypy clean)
- [x] S3 implemented and tested (113 tests)
- [x] S4 implemented and tested (126 tests)
- [x] S5 implemented and tested (134 tests)
- [x] S1 implemented — all 5 consumer requirements.txt updated to `git+https://github.com/exPardus/expardus_tracing.git@v0.1.0`
- [x] Full test suite green after all changes (134/134 passed, mypy strict clean)

## Breaking Change Notice

`extract_trace_from_headers()` now returns a 3-tuple `(trace_id, parent_span_id, tracestate)` instead of a 2-tuple. Consumers that destructure the result need updating. Known affected:
- `expardus_api` — `RequestTracingMiddleware`
- Any other code calling `extract_trace_from_headers()`
