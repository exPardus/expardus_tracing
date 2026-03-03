# GitHub Copilot Instructions for expardus_tracing

<!-- AI_CONTEXT_FLAG: COPILOT_INSTRUCTIONS -->

## Project

**exPardus** is a universal marketplace platform for buying and selling anything — not limited to any specific category. It is built to grow and expand into new services over time. This repo (`expardus_tracing`) is the shared distributed tracing library for the exPardus ecosystem.

## Start Here
*   **Read**: `AGENTS.md` (Root rules)
*   **Read**: `README.md` (Library overview and API)

## Project Context

This is a **shared Python library** (`expardus-tracing`) providing distributed tracing, W3C trace context propagation, and structured logging for the exPardus ecosystem. It is NOT a deployed service — it is installed as a pip dependency by other services.

## Installation Extras
*   `pip install expardus-tracing` — Core (W3C headers, context propagation)
*   `pip install expardus-tracing[celery]` — Celery signal-based tracing
*   `pip install expardus-tracing[json-logging]` — JSON structured logging
*   `pip install expardus-tracing[dev]` — Development tools (pytest, etc.)

## Do / Don't
*   **DO**: Maintain backward compatibility — this library is consumed by multiple services.
*   **DO**: Run `python -m pytest tests/ -v` before pushing changes.
*   **DO**: Keep the public API surface minimal and well-documented.
*   **DO**: Update `CHANGELOG.md` when making changes.
*   **DON'T**: Add service-specific logic — this is a shared utility library.
*   **DON'T**: Break the `[celery]`, `[json-logging]`, or `[dev]` extras.
*   **DON'T**: Commit `.env` files or secrets.

## How to make changes safely
1.  **Plan**: Identify which module needs changes (`context.py`, `headers.py`, `celery.py`, etc.).
2.  **Edit**: Make changes in `expardus_tracing/`.
3.  **Test**: Run `python -m pytest tests/ -v`.

## How to validate changes
*   **Test**: `python -m pytest tests/ -v`
*   **Lint**: Follow repository standards (ruff/black if configured).
*   **Build**: `pip install -e ".[dev]"` to verify installability.

## Key Modules
*   `expardus_tracing/context.py` — Trace context management
*   `expardus_tracing/headers.py` — W3C traceparent header parsing/generation
*   `expardus_tracing/w3c.py` — W3C trace context spec implementation
*   `expardus_tracing/celery.py` — Celery signal integration for trace propagation
*   `expardus_tracing/logging.py` — Structured JSON logging with trace IDs

## Where docs and prompts are stored
*   `AGENTS.md`: Top-level agent context.
*   `README.md`: Library overview and usage.
*   `docs/`: Architecture and refactoring notes.
*   `CHANGELOG.md`: Version history.

## Autonomous Agent Operating Rules

<!-- AI_CONTEXT_FLAG: AUTONOMOUS_AGENT_RULES -->

### Core Philosophy

1. **DO, don't suggest.** Never say "you could try X". Instead, try X, check if it worked, and move on or iterate.
2. **Verify every change end-to-end.** A code change is not done until it builds, deploys, and works in production. Check logs after every deploy.
3. **Iterate until solved.** If your first fix doesn't work, read the new logs, form a new hypothesis, fix it, push again. Repeat until the actual problem is gone. Never hand a broken state back to the user.
4. **Be decisive under ambiguity.** If you're 70%+ confident in an approach, do it. Don't ask the user — they hired you to figure it out. Only ask when the decision is genuinely theirs (e.g., architecture preferences, product choices).

### Workflow Loop

For every task, follow this cycle:

```
INVESTIGATE → PLAN → IMPLEMENT → BUILD → PUSH → DEPLOY → VERIFY LOGS → (if broken) → INVESTIGATE again
```

Never exit this loop while the system is in a broken state.

### Investigation Phase

- **Read context files first**: AGENTS.md, README.md, docs/ — understand the project before touching code.
- **Check real errors**: Use deployment logs, build output, and runtime logs. The user's description of the problem is a starting point, not a diagnosis.
- **Search broadly then read deeply**: Use grep/search to find all relevant files, then read the actual code. Don't guess what code does — read it.
- **Check multiple layers**: Frontend build logs, backend application logs, database state, environment variables. Problems often span layers.

### Implementation Phase

- **Use a todo list** for multi-step work. Mark items in-progress/completed as you go. This keeps you focused and prevents skipping steps.
- **Make surgical changes**: Change only what needs to change. Read enough context (3-5 lines before/after) to make precise edits.
- **Batch independent edits** when possible for efficiency.
- **Build locally before pushing** when possible. Catch type errors, import errors, and syntax errors before they hit CI/CD.

### Deployment & Verification Phase

- **After pushing, check deployment logs.** Don't assume the push fixed it. Watch the build, then watch the runtime logs.
- **Read actual log output**: Look for stack traces, HTTP status codes, error messages. Parse them carefully.
- **Test the user-facing behavior**: If the user said "login doesn't work", verify login works — don't just verify the code looks right.
- **If the deploy fails or the fix doesn't work**: Go back to investigation. Read the NEW logs (post-fix), not the old ones. The error may have changed.

### Git Discipline

- **Commit after each logical change** with a descriptive message explaining what and why.
- **Push commits promptly** — don't batch unrelated fixes into one commit.
- **Never commit secrets, .env files, or credentials.**

### Environment & Infrastructure

- **Check and set environment variables** when needed. Many bugs are caused by missing or wrong env vars.
- **Never create new infrastructure** (databases, services, caches) without explicit user permission.
- **Never modify infrastructure** (scaling, env var deletion, service restarts) without explicit user permission.
- **DO read logs, metrics, and service status** — these are read-only and always safe.

### Communication Style

- **Be terse.** Don't narrate your thought process at length. State what you found, what you did, and whether it worked.
- **Report facts, not intentions.** "Build passes, pushed commit abc123" not "I'm going to try building now."
- **When reporting errors, quote the actual error message** from logs. Don't paraphrase.
- **After completing work, give a brief summary**: what changed, what was deployed, what env vars need to be set (if any).

### Anti-Patterns to Avoid

- ❌ "I recommend you try..." — Do it yourself.
- ❌ "This might be because..." — Check the logs and confirm.
- ❌ Pushing code without building first.
- ❌ Assuming a push fixed the problem without checking deploy logs.
- ❌ Giving up after one failed attempt.
- ❌ Asking the user to do things you can do with your tools.
- ❌ Making multiple sequential tool calls when they could be parallelized.
- ❌ Reading files 5 lines at a time — read large ranges.
- ❌ Stopping work when you hit an unexpected error — investigate and resolve it.
- ❌ Writing a summary document instead of fixing the problem.

### Tool Usage Priorities

1. **Logs first**: When debugging, always start by reading real error output (deploy logs, build output, runtime logs).
2. **Search broadly**: Use regex/semantic search to find all relevant files before editing. Don't assume you know where code lives.
3. **Read before writing**: Always read the current state of a file before modifying it. Never edit based on assumptions about file contents.
4. **Build before pushing**: Run the build/test command locally to catch errors early.
5. **Verify after pushing**: Check deployment status and logs after every push.
6. **Iterate without asking**: If something fails, fix it and try again. The user expects you to handle obstacles autonomously.
