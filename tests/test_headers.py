"""Tests for expardus_tracing.headers module."""
from __future__ import annotations

import pytest

from expardus_tracing.context import clear_trace_context, set_trace_context
from expardus_tracing.headers import (
    CELERY_SPAN_ID_KEY,
    CELERY_TRACE_ID_KEY,
    CELERY_TRACEPARENT_KEY,
    REQUEST_ID_HEADER,
    TRACE_ID_HEADER,
    TRACEPARENT_HEADER,
    extract_trace_from_celery_headers,
    extract_trace_from_headers,
    extract_trace_from_task_headers,
    get_celery_trace_headers,
    get_http_trace_headers,
    get_trace_headers,
    get_trace_headers_for_task,
)


class TestExtractTraceFromHeaders:
    def test_none_headers(self):
        assert extract_trace_from_headers(None) == (None, None)

    def test_empty_headers(self):
        assert extract_trace_from_headers({}) == (None, None)

    def test_traceparent(self):
        headers = {
            "traceparent": "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"
        }
        tid, psid = extract_trace_from_headers(headers)
        assert tid == "0af7651916cd43dd8448eb211c80319c"
        assert psid == "b7ad6b7169203331"

    def test_x_trace_id(self):
        headers = {"x-trace-id": "a" * 32}
        tid, psid = extract_trace_from_headers(headers)
        assert tid == "a" * 32
        assert psid is None

    def test_x_request_id(self):
        headers = {"x-request-id": "b" * 32}
        tid, psid = extract_trace_from_headers(headers)
        assert tid == "b" * 32
        assert psid is None

    def test_priority_traceparent_over_trace_id(self):
        headers = {
            "traceparent": "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01",
            "x-trace-id": "c" * 32,
        }
        tid, _ = extract_trace_from_headers(headers)
        assert tid == "0af7651916cd43dd8448eb211c80319c"

    def test_case_insensitive(self):
        headers = {"X-Trace-ID": "d" * 32}
        tid, _ = extract_trace_from_headers(headers)
        assert tid == "d" * 32

    def test_invalid_trace_id_rejected(self):
        headers = {"x-trace-id": "not-hex"}
        assert extract_trace_from_headers(headers) == (None, None)

    def test_16_char_trace_id_accepted(self):
        headers = {"x-trace-id": "a" * 16}
        tid, _ = extract_trace_from_headers(headers)
        assert tid == "a" * 16


class TestExtractCeleryHeaders:
    def test_none(self):
        assert extract_trace_from_celery_headers(None) == (None, None)

    def test_traceparent(self):
        headers = {
            CELERY_TRACEPARENT_KEY: "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"
        }
        tid, psid = extract_trace_from_celery_headers(headers)
        assert tid == "0af7651916cd43dd8448eb211c80319c"

    def test_simple_trace_id(self):
        headers = {CELERY_TRACE_ID_KEY: "e" * 32}
        tid, psid = extract_trace_from_celery_headers(headers)
        assert tid == "e" * 32
        assert psid is None

    def test_trace_id_with_span(self):
        headers = {
            CELERY_TRACE_ID_KEY: "f" * 32,
            CELERY_SPAN_ID_KEY: "1" * 16,
        }
        tid, psid = extract_trace_from_celery_headers(headers)
        assert tid == "f" * 32
        assert psid == "1" * 16

    def test_task_headers_alias(self):
        """extract_trace_from_task_headers should be the same function."""
        headers = {CELERY_TRACE_ID_KEY: "g" * 32}
        assert extract_trace_from_task_headers(headers) == extract_trace_from_celery_headers(headers)


class TestGetTraceHeaders:
    def setup_method(self):
        clear_trace_context()

    def teardown_method(self):
        clear_trace_context()

    def test_no_context(self):
        assert get_trace_headers() == {}
        assert get_http_trace_headers() == {}

    def test_with_context(self):
        set_trace_context(trace_id="a" * 32, span_id="b" * 16)
        headers = get_trace_headers()
        assert headers[TRACE_ID_HEADER] == "a" * 32
        assert "traceparent" in headers

    def test_http_headers(self):
        set_trace_context(trace_id="a" * 32, span_id="b" * 16)
        headers = get_http_trace_headers()
        assert headers["X-Trace-ID"] == "a" * 32
        assert "traceparent" in headers


class TestGetCeleryTraceHeaders:
    def setup_method(self):
        clear_trace_context()

    def teardown_method(self):
        clear_trace_context()

    def test_no_context(self):
        assert get_celery_trace_headers() == {}
        assert get_trace_headers_for_task() == {}

    def test_with_context(self):
        set_trace_context(trace_id="a" * 32, span_id="b" * 16)
        headers = get_celery_trace_headers()
        assert headers[CELERY_TRACE_ID_KEY] == "a" * 32
        assert headers[CELERY_SPAN_ID_KEY] == "b" * 16
        assert CELERY_TRACEPARENT_KEY in headers

    def test_roundtrip(self):
        """Headers produced by get_celery_trace_headers should be parseable."""
        set_trace_context(trace_id="a" * 32, span_id="b" * 16)
        headers = get_celery_trace_headers()
        tid, psid = extract_trace_from_celery_headers(headers)
        assert tid == "a" * 32
        assert psid == "b" * 16

    def test_for_task_alias(self):
        set_trace_context(trace_id="a" * 32, span_id="b" * 16)
        assert get_trace_headers_for_task() == get_celery_trace_headers()


class TestHeaderConstants:
    def test_constants_exist(self):
        assert TRACEPARENT_HEADER == "traceparent"
        assert TRACE_ID_HEADER == "x-trace-id"
        assert REQUEST_ID_HEADER == "x-request-id"
        assert CELERY_TRACE_ID_KEY == "trace_id"
        assert CELERY_SPAN_ID_KEY == "parent_span_id"
        assert CELERY_TRACEPARENT_KEY == "traceparent"
