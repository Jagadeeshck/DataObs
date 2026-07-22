import pytest

from services.data_products.dependency_events import canonical_upstream_ids, dependency_request_fingerprint
from services.data_products.idempotency import hash_key


def test_raw_idempotency_key_is_not_the_persisted_identity():
    secret = "secret-sentinel-client-key"
    assert secret not in hash_key(secret)


def test_fingerprint_binds_actor_reason_etag_and_empty_transition():
    base = dict(tenant_id="t", environment="prod", product_id="p", actor="a", reason="r", expected_product_etag='"1"')
    empty = dependency_request_fingerprint(upstream_product_ids=[], **base)
    assert empty != dependency_request_fingerprint(upstream_product_ids=["u"], **base)
    assert empty != dependency_request_fingerprint(upstream_product_ids=[], **{**base, "actor": "b"})
    assert empty != dependency_request_fingerprint(upstream_product_ids=[], **{**base, "reason": "other"})
    assert empty != dependency_request_fingerprint(upstream_product_ids=[], **{**base, "expected_product_etag": '"2"'})


def test_amplification_and_self_reference_are_bounded():
    with pytest.raises(ValueError, match="count"):
        canonical_upstream_ids("p", [f"u-{n}" for n in range(4)], maximum=3)
    with pytest.raises(ValueError, match="self"):
        canonical_upstream_ids("p", ["p"])
