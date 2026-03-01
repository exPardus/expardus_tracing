"""
W3C Traceparent Parsing and Formatting

Implements parsing and formatting for the W3C Trace Context ``traceparent``
header (https://www.w3.org/TR/trace-context/).

Format: ``{version}-{trace_id}-{parent_span_id}-{flags}``
Example: ``00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01``
"""
from __future__ import annotations


def parse_traceparent(traceparent: str | None) -> tuple[str | None, str | None]:
    """
    Parse a W3C traceparent header.

    Returns:
        (trace_id, parent_span_id) or (None, None) if invalid/missing.
    """
    if not traceparent:
        return None, None

    try:
        parts = traceparent.split("-")
        if len(parts) != 4 or parts[0] != "00":
            return None, None

        trace_id, parent_span_id = parts[1], parts[2]

        if len(trace_id) != 32 or not all(
            c in "0123456789abcdef" for c in trace_id.lower()
        ):
            return None, None
        if trace_id == "0" * 32:
            return None, None

        if len(parent_span_id) != 16 or not all(
            c in "0123456789abcdef" for c in parent_span_id.lower()
        ):
            return None, None

        return trace_id.lower(), parent_span_id.lower()
    except Exception:
        return None, None


def format_traceparent(
    trace_id: str, span_id: str, sampled: bool = True
) -> str:
    """Format a W3C traceparent header value."""
    flags = "01" if sampled else "00"
    return f"00-{trace_id}-{span_id}-{flags}"
