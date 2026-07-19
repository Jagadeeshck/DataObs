import time

import pytest

from services.product_query.stream_pagination import CursorCodec, CursorState, InvalidCursor


def test_cursor_round_trip_and_context_binding():
    codec = CursorCodec("a-secret-with-enough-bytes", ttl_seconds=60)
    cursor = codec.encode(CursorState(["orders", "id-1"]), tenant="acme", environment="prod", filters={"q": "ord"})
    assert codec.decode(cursor, tenant="acme", environment="prod", filters={"q": "ord"}).sort == ["orders", "id-1"]
    with pytest.raises(InvalidCursor, match="context"):
        codec.decode(cursor, tenant="other", environment="prod", filters={"q": "ord"})
    with pytest.raises(InvalidCursor, match="filters"):
        codec.decode(cursor, tenant="acme", environment="prod", filters={"q": "payments"})


def test_cursor_rejects_tampering_and_expiry():
    codec = CursorCodec("a-secret-with-enough-bytes", ttl_seconds=-1)
    cursor = codec.encode(CursorState([1]), tenant="acme", environment="prod", filters={})
    with pytest.raises(InvalidCursor, match="expired"):
        codec.decode(cursor, tenant="acme", environment="prod", filters={})
    codec = CursorCodec("a-secret-with-enough-bytes")
    cursor = codec.encode(CursorState([1]), tenant="acme", environment="prod", filters={})
    with pytest.raises(InvalidCursor, match="signature"):
        codec.decode(cursor[:-1] + ("A" if cursor[-1] != "A" else "B"), tenant="acme", environment="prod", filters={})
