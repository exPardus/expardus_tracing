# expardus_tracing - CLAUDE.md

Shared Python library providing distributed tracing, W3C trace context propagation, and structured logging for the **exPardus** ecosystem.

## Quick Orientation

- **Read first**: `AGENTS.md`, `README.md`, `CHANGELOG.md`
- This is a **pip-installable library**, NOT a deployed service
- Consumed by: `expardus_api`, `celery_backround_workers`, `expardus_telegram_bot`

## Install Extras

```bash
pip install expardus-tracing              # Core (W3C headers, context propagation)
pip install expardus-tracing[celery]      # Celery signal-based tracing
pip install expardus-tracing[json-logging] # JSON structured logging
pip install expardus-tracing[dev]         # Development tools (pytest, etc.)
```

## Commands

```bash
python -m pytest tests/ -v       # run all tests
pip install -e ".[dev]"          # install editable + dev deps
```

## Key Modules

| Module | Purpose |
|--------|---------|
| `expardus_tracing/context.py` | Trace context management |
| `expardus_tracing/headers.py` | W3C traceparent header parsing/generation |
| `expardus_tracing/w3c.py` | W3C trace context spec implementation |
| `expardus_tracing/celery.py` | Celery signal integration for trace propagation |
| `expardus_tracing/logging.py` | Structured JSON logging with trace IDs |

## Key Rules

- **Backward compatibility is critical** — multiple services depend on this library
- Keep the public API surface minimal and well-documented
- Update `CHANGELOG.md` when making changes
- Don't add service-specific logic — this is a shared utility library
- Don't break the `[celery]`, `[json-logging]`, or `[dev]` extras
- W3C Trace Context spec compliance required
- All modules must have corresponding tests in `tests/`
