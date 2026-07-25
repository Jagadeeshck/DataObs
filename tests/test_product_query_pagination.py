import pytest

from services.product_query.pagination import decode_cursor, encode_cursor


def test_cursor_round_trip_is_opaque_and_preserves_search_after_values():
    cursor = encode_cursor(["Orders", "asset-42"])
    assert "Orders" not in cursor
    assert decode_cursor(cursor) == ["Orders", "asset-42"]


@pytest.mark.parametrize("cursor", ["not-base64", "e30", "eyJ2IjoyLCJzb3J0IjpbXX0"])
def test_cursor_rejects_invalid_or_tampered_values(cursor):
    with pytest.raises(ValueError):
        decode_cursor(cursor)
