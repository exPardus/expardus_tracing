# Refactor Plan: Strategic Improvements (S1–S5)

> Date: 2026-03-02

## Target Architecture

Add four new capabilities to the shared tracing library:
1. **PEP 561 type marker** (S2) — enables downstream type checking
2. **W3C tracestate** (S3) — completes W3C Trace Context compliance
3. **Sampling flags** (S4) — propagates sampled/unsampled decisions
4. **@traced() decorator** (S5) — ergonomic span creation
5. **Git-based install** (S1) — makes package installable outside dev machine

## Boundaries & Non-Goals

- **Non-goal**: Full OpenTelemetry SDK integration (out of scope)
- **Non-goal**: Changing internal ContextVar mechanics
- **Non-goal**: Breaking backward compatibility with existing consumers
- **Boundary**: Only `expardus_tracing/` source and consumer `requirements.txt` are modified

## Step-by-Step Migration

### Step 1: S2 — `py.typed` + mypy config (no code changes)
- Create `expardus_tracing/py.typed` (empty marker)
- Add `[tool.mypy]` to `pyproject.toml`
- Run mypy and fix any strict-mode issues
- **Verify**: existing tests pass, mypy passes

### Step 2: S3 — `tracestate` support
- Add `parse_tracestate()` and `format_tracestate()` to `w3c.py`
- Add `tracestate: dict[str, str]` field to `TraceContext` dataclass
- Update `set_trace_context()` to accept optional `tracestate`
- Update `extract_trace_from_headers()` to extract tracestate
- Update `get_trace_headers()` to emit tracestate when present
- Add `TRACESTATE_HEADER` constant to `headers.py`
- Re-export new symbols from `__init__.py`
- Add tests
- **Verify**: all tests pass

### Step 3: S4 — Sampling decision propagation
- Add `sampled: bool = True` field to `TraceContext`
- Add `parse_traceparent_full()` to `w3c.py`
- Update `set_trace_context()` to accept optional `sampled`
- Update header injection to use context's sampled flag
- Re-export from `__init__.py`
- Add tests
- **Verify**: all tests pass, `parse_traceparent()` unchanged

### Step 4: S5 — `@traced()` decorator
- Add `traced()` function to `context.py`
- Handle both sync and async functions
- Re-export from `__init__.py`
- Add tests (sync, async, nested)
- **Verify**: all tests pass

### Step 5: S1 — Replace local file path installs (LAST)
- Update all 5 consumer `requirements.txt` files
- Replace `file:///` with `git+https://` URL pinned to `@main`
- **Verify**: pip install works, consumer tests pass

## Rollback Strategy

Each step is independently reversible:
- S2: Delete `py.typed`, remove `[tool.mypy]` section
- S3: Remove tracestate functions/field, revert header changes
- S4: Remove `sampled` field and `parse_traceparent_full`
- S5: Remove `traced()` function
- S1: Revert `requirements.txt` to local file path
