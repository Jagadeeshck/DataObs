from services.data_products.cursors import CursorContext, InvalidCursor, SignedCursorCodec


def test_cursor_is_bound_to_scope_route_filters_and_expiry():
    codec = SignedCursorCodec(b"a" * 32, ttl_seconds=60)
    context = CursorContext("products", "tenant-a", "prod", {"state": "active"})
    encoded = codec.encode(context, ["orders", "tie"], now=100)
    assert codec.decode(encoded, context, now=120) == ["orders", "tie"]

    for other in (
        CursorContext("revisions", "tenant-a", "prod", {"state": "active"}),
        CursorContext("products", "tenant-b", "prod", {"state": "active"}),
        CursorContext("products", "tenant-a", "prod", {"state": "draft"}),
    ):
        try:
            codec.decode(encoded, other, now=120)
        except InvalidCursor:
            pass
        else:
            raise AssertionError("cursor replay must fail closed")

    try:
        codec.decode(encoded, context, now=161)
    except InvalidCursor:
        pass
    else:
        raise AssertionError("expired cursor must fail closed")


def test_cursor_tampering_is_rejected():
    codec = SignedCursorCodec(b"b" * 32)
    context = CursorContext("products", "tenant-a", "prod", {})
    encoded = codec.encode(context, ["orders"], now=100)
    replacement = "A" if encoded[-1] != "A" else "B"
    try:
        codec.decode(encoded[:-1] + replacement, context, now=101)
    except InvalidCursor:
        return
    raise AssertionError("tampered cursor must fail closed")
