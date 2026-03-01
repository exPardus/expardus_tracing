"""Tests for expardus_tracing.w3c module."""
from __future__ import annotations

import pytest

from expardus_tracing.w3c import format_traceparent, parse_traceparent


class TestParseTraceparent:
    def test_valid(self):
        tid, psid = parse_traceparent(
            "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"
        )
        assert tid == "0af7651916cd43dd8448eb211c80319c"
        assert psid == "b7ad6b7169203331"

    def test_none(self):
        assert parse_traceparent(None) == (None, None)

    def test_empty(self):
        assert parse_traceparent("") == (None, None)

    def test_wrong_version(self):
        assert parse_traceparent(
            "01-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"
        ) == (None, None)

    def test_wrong_parts(self):
        assert parse_traceparent("00-abc-01") == (None, None)

    def test_short_trace_id(self):
        assert parse_traceparent("00-abc-b7ad6b7169203331-01") == (None, None)

    def test_invalid_hex_trace_id(self):
        assert parse_traceparent(
            "00-ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ-b7ad6b7169203331-01"
        ) == (None, None)

    def test_all_zero_trace_id(self):
        assert parse_traceparent(
            "00-00000000000000000000000000000000-b7ad6b7169203331-01"
        ) == (None, None)

    def test_short_span_id(self):
        assert parse_traceparent(
            "00-0af7651916cd43dd8448eb211c80319c-abc-01"
        ) == (None, None)

    def test_uppercase_normalised(self):
        tid, psid = parse_traceparent(
            "00-0AF7651916CD43DD8448EB211C80319C-B7AD6B7169203331-01"
        )
        assert tid == "0af7651916cd43dd8448eb211c80319c"
        assert psid == "b7ad6b7169203331"

    def test_unsampled_flag(self):
        """Flags don't affect parse_traceparent (only parse_traceparent_full uses them)."""
        tid, psid = parse_traceparent(
            "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-00"
        )
        assert tid is not None


class TestFormatTraceparent:
    def test_sampled(self):
        result = format_traceparent("a" * 32, "b" * 16, sampled=True)
        assert result == f"00-{'a'*32}-{'b'*16}-01"

    def test_unsampled(self):
        result = format_traceparent("a" * 32, "b" * 16, sampled=False)
        assert result == f"00-{'a'*32}-{'b'*16}-00"

    def test_default_sampled(self):
        result = format_traceparent("a" * 32, "b" * 16)
        assert result.endswith("-01")

    def test_roundtrip(self):
        original_tid = "0af7651916cd43dd8448eb211c80319c"
        original_sid = "b7ad6b7169203331"
        formatted = format_traceparent(original_tid, original_sid)
        parsed_tid, parsed_sid = parse_traceparent(formatted)
        assert parsed_tid == original_tid
        assert parsed_sid == original_sid
