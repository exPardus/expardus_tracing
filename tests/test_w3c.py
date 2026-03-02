"""Tests for expardus_tracing.w3c module."""
from __future__ import annotations

import pytest

from expardus_tracing.w3c import (
    format_traceparent,
    format_tracestate,
    parse_traceparent,
    parse_traceparent_full,
    parse_tracestate,
)


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


class TestParseTraceparentFull:
    def test_sampled(self):
        tid, psid, sampled = parse_traceparent_full(
            "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"
        )
        assert tid == "0af7651916cd43dd8448eb211c80319c"
        assert psid == "b7ad6b7169203331"
        assert sampled is True

    def test_unsampled(self):
        tid, psid, sampled = parse_traceparent_full(
            "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-00"
        )
        assert tid == "0af7651916cd43dd8448eb211c80319c"
        assert sampled is False

    def test_none(self):
        assert parse_traceparent_full(None) == (None, None, True)

    def test_empty(self):
        assert parse_traceparent_full("") == (None, None, True)

    def test_invalid(self):
        assert parse_traceparent_full("invalid") == (None, None, True)

    def test_flags_hex_02(self):
        """Flag 0x02 — sampled bit not set."""
        _, _, sampled = parse_traceparent_full(
            "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-02"
        )
        assert sampled is False

    def test_flags_hex_03(self):
        """Flag 0x03 — sampled bit set (bit 0)."""
        _, _, sampled = parse_traceparent_full(
            "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-03"
        )
        assert sampled is True

    def test_roundtrip_sampled(self):
        tid = "0af7651916cd43dd8448eb211c80319c"
        sid = "b7ad6b7169203331"
        formatted = format_traceparent(tid, sid, sampled=True)
        p_tid, p_sid, p_sampled = parse_traceparent_full(formatted)
        assert p_tid == tid
        assert p_sid == sid
        assert p_sampled is True

    def test_roundtrip_unsampled(self):
        tid = "0af7651916cd43dd8448eb211c80319c"
        sid = "b7ad6b7169203331"
        formatted = format_traceparent(tid, sid, sampled=False)
        p_tid, p_sid, p_sampled = parse_traceparent_full(formatted)
        assert p_tid == tid
        assert p_sid == sid
        assert p_sampled is False


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


class TestParseTracestate:
    def test_none(self):
        assert parse_tracestate(None) == {}

    def test_empty(self):
        assert parse_tracestate("") == {}

    def test_single_member(self):
        assert parse_tracestate("vendor=value") == {"vendor": "value"}

    def test_multiple_members(self):
        result = parse_tracestate("vendor1=value1,vendor2=value2")
        assert result == {"vendor1": "value1", "vendor2": "value2"}

    def test_whitespace_trimmed(self):
        result = parse_tracestate(" vendor1 = value1 , vendor2 = value2 ")
        assert result == {"vendor1": "value1", "vendor2": "value2"}

    def test_empty_value_preserved(self):
        result = parse_tracestate("vendor=")
        assert result == {"vendor": ""}

    def test_equals_in_value(self):
        result = parse_tracestate("vendor=a=b=c")
        assert result == {"vendor": "a=b=c"}

    def test_empty_key_skipped(self):
        result = parse_tracestate("=value,real=data")
        assert result == {"real": "data"}

    def test_no_equals_member_skipped(self):
        result = parse_tracestate("invalid,real=data")
        assert result == {"real": "data"}


class TestFormatTracestate:
    def test_empty_dict(self):
        assert format_tracestate({}) == ""

    def test_single(self):
        assert format_tracestate({"vendor": "value"}) == "vendor=value"

    def test_multiple(self):
        result = format_tracestate({"a": "1", "b": "2"})
        assert "a=1" in result
        assert "b=2" in result

    def test_roundtrip(self):
        original = {"vendor1": "value1", "vendor2": "value2"}
        header = format_tracestate(original)
        parsed = parse_tracestate(header)
        assert parsed == original
