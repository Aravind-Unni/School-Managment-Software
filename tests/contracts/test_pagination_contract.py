"""Collections return items and next_cursor. Cursors stay opaque."""

from __future__ import annotations

import pytest

from contracts.pagination import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    Page,
    clamp_page_size,
    decode_cursor,
    encode_cursor,
)

pytestmark = pytest.mark.contract


def test_page_wire_shape_is_items_and_next_cursor():
    assert set(Page(items=(), next_cursor=None).to_wire()) == {"items", "next_cursor"}


def test_last_page_has_null_next_cursor():
    assert Page(items=(1, 2)).to_wire()["next_cursor"] is None


def test_cursor_round_trips():
    position = {"created_at": "2026-07-15T04:30:00+00:00", "id": "abc"}
    assert decode_cursor(encode_cursor(position)) == position


def test_cursor_is_url_safe_and_unpadded():
    cursor = encode_cursor({"id": "a" * 40})
    assert "=" not in cursor
    assert "+" not in cursor and "/" not in cursor


@pytest.mark.parametrize("bad", ["", "not-base64!!", "YWJj", "e30"])
def test_malformed_cursor_raises_value_error_not_a_crash(bad):
    # The view turns this into 422; it must never be a 500.
    with pytest.raises(ValueError):
        decode_cursor(bad)


@pytest.mark.parametrize(
    ("requested", "expected"),
    [
        (None, DEFAULT_PAGE_SIZE),
        (0, DEFAULT_PAGE_SIZE),
        (-5, DEFAULT_PAGE_SIZE),
        (10, 10),
        (MAX_PAGE_SIZE, MAX_PAGE_SIZE),
        (MAX_PAGE_SIZE + 1, MAX_PAGE_SIZE),
        (10_000, MAX_PAGE_SIZE),
    ],
)
def test_page_size_is_clamped_so_no_list_is_unbounded(requested, expected):
    assert clamp_page_size(requested) == expected
