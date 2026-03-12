# Security Tests - expardus_tracing

**Last Updated:** July 25, 2026

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

### How to Extend

Add security tests to the relevant test file (e.g., `test_w3c.py` for parsing, `test_logging.py` for log safety):

```python
def test_new_security_property(self):
    """SEC-ET-XXX: Description of security property being tested."""
    # assertion
```
