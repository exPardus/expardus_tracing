# Changelog

All notable changes to `expardus-tracing` will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-03-02

### Added
- **Core context management** (`context.py`): `TraceContext` dataclass, `ContextVar`-based storage, `set_trace_context`, `get_trace_context`, `clear_trace_context`, `bind_context`, `trace_context_scope`, `trace_span`.
- **ID generation**: `generate_trace_id()` (32 hex, 128-bit) and `generate_span_id()` (16 hex, 64-bit) using `secrets.token_hex`.
- **W3C Trace Context** (`w3c.py`): `parse_traceparent` and `format_traceparent` implementing the W3C `traceparent` header spec (version `00`).
- **HTTP header helpers** (`headers.py`): `extract_trace_from_headers` (with priority: `traceparent` → `x-trace-id` → `x-request-id`), `get_trace_headers`, `get_http_trace_headers`.
- **Celery header helpers** (`headers.py`): `extract_trace_from_celery_headers`, `get_celery_trace_headers`, `get_trace_headers_for_task`.
- **Celery signal integration** (`celery.py`): `setup_celery_tracing()` registering `before_task_publish`, `task_prerun`, `task_postrun`, `task_failure`, `task_retry` handlers with `weak=False`.
- **Structured logging** (`logging.py`): `TraceContextFilter` injecting `trace_id`, `span_id`, `service`, `env`, `release` into log records. `setup_logging()` configuring JSON-formatted root logger.
- **Optional OTel bridge**: Graceful degradation when `otel_worker` module is not available.
- **81 unit + integration tests** covering all modules including full Celery lifecycle propagation.
- Header constants: `TRACEPARENT_HEADER`, `TRACE_ID_HEADER`, `REQUEST_ID_HEADER`, `CELERY_TRACE_ID_KEY`, `CELERY_SPAN_ID_KEY`, `CELERY_TRACEPARENT_KEY`.
- Package-level config: `SERVICE_NAME`, `ENV`, `RELEASE` (env-var driven).

### Fixed
- `trace_span()` now stores the `operation` parameter in `ctx.extra["operation"]`.
- `get_http_trace_headers()` now uses the `TRACE_ID_HEADER` constant (`x-trace-id`) consistently with `get_trace_headers()`, instead of hardcoded `X-Trace-ID`.
- `pythonjsonlogger` import updated to prefer the non-deprecated `pythonjsonlogger.json.JsonFormatter` path, with fallback to `pythonjsonlogger.jsonlogger.JsonFormatter`.
