"""
W3C Traceparent and Tracestate Parsing and Formatting

Implements parsing and formatting for the W3C Trace Context ``traceparent``
and ``tracestate`` headers (https://www.w3.org/TR/trace-context/).

traceparent format: ``{version}-{trace_id}-{parent_span_id}-{flags}``
Example: ``00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01``

tracestate format: ``key1=value1,key2=value2``
"""
from __future__ import annotations


def _is_valid_hex(s: str) -> bool:
    """Check if a string contains only hexadecimal characters."""
    try:
        int(s, 16)
        return True
    except ValueError:
        return False


def parse_traceparent(traceparent: str | None) -> tuple[str | None, str | None]:
    """
    Parse a W3C traceparent header.

    Returns:
        (trace_id, parent_span_id) or (None, None) if invalid/missing.
    """
    tid, sid, _ = parse_traceparent_full(traceparent)
    return tid, sid


def format_traceparent(
    trace_id: str, span_id: str, sampled: bool = True
) -> str:
    """Format a W3C traceparent header value."""
    flags = "01" if sampled else "00"
    return f"00-{trace_id}-{span_id}-{flags}"


def parse_traceparent_full(
    traceparent: str | None,
) -> tuple[str | None, str | None, bool]:
    """
    Parse a W3C traceparent header, including the sampled flag.

    Returns:
        (trace_id, parent_span_id, sampled). Returns ``(None, None, True)``
        if the header is invalid or missing (default sampled=True).
    """
    if not traceparent:
        return None, None, True

    try:
        parts = traceparent.split("-")
        if len(parts) != 4 or parts[0] != "00":
            return None, None, True

        trace_id, parent_span_id, flags_str = parts[1], parts[2], parts[3]

        if len(trace_id) != 32 or not _is_valid_hex(trace_id):
            return None, None, True
        if trace_id == "0" * 32:
            return None, None, True

        if len(parent_span_id) != 16 or not _is_valid_hex(parent_span_id):
            return None, None, True

        # Parse flags — bit 0 is the sampled flag
        try:
            flags = int(flags_str, 16)
        except ValueError:
            flags = 1  # default sampled
        sampled = bool(flags & 0x01)

        return trace_id.lower(), parent_span_id.lower(), sampled
    except Exception:
        return None, None, True


# =============================================================================
# Tracestate
# =============================================================================


def parse_tracestate(header: str | None) -> dict[str, str]:
    """
    Parse a W3C tracestate header into key-value pairs.

    The tracestate header carries vendor-specific trace context as
    comma-separated ``key=value`` members.

    Keys starting with ``_`` are rejected (defense-in-depth against
    dunder attribute injection when values are later set on log records).
    At most 32 members are accepted per the W3C specification.

    Returns:
        A dict of key-value pairs. Empty dict if header is absent or empty.
    """
    if not header:
        return {}
    result: dict[str, str] = {}
    for member in header.split(","):
        member = member.strip()
        if "=" in member:
            key, value = member.split("=", 1)
            key = key.strip()
            value = value.strip()
            if key and not key.startswith("_") and len(key) <= 256 and len(value) <= 256:
                result[key] = value
                if len(result) >= 32:
                    break
    return result


def format_tracestate(state: dict[str, str]) -> str:
    """
    Format a tracestate dict into a W3C tracestate header value.

    Returns:
        Comma-separated ``key=value`` string. Empty string if dict is empty.
    """
    if not state:
        return ""
    return ",".join(f"{k}={v}" for k, v in state.items())
