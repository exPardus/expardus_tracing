# Refactor Log — expardus_tracing

## 2026-03-13

### refactor: deduplicate W3C traceparent parsing
- `w3c.py`: `parse_traceparent()` now delegates to `parse_traceparent_full()` instead of duplicating all validation logic.
- Added `_is_valid_hex()` helper using `int(s, 16)` — replaces verbose `all(c in "..." for c)` pattern.

### perf: faster hex validation in headers.py
- `headers.py`: `_is_valid_trace_id()` now uses `int(trace_id, 16)` try/except instead of character-by-character iteration.

### refactor: remove unused _service_name in logging.py
- Removed dead `_service_name` module-level variable that was shadowed by `setup_logging()` imports.
