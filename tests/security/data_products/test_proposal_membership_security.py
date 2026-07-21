from services.data_products.membership_events import MembershipMutation


def test_decision_fingerprint_binds_actor_reason_revision_and_never_contains_raw_key():
    base = dict(
        tenant_id="tenant",
        environment="prod",
        product_id="product",
        action="accept",
        actor="actor",
        reason="reason",
        idempotency_key="secret-sentinel",
        body={"proposal_id": "proposal"},
        expected_revision=1,
    )
    mutation = MembershipMutation(**base)
    assert "secret-sentinel" not in repr(mutation.event(outcome="pending", proposal_id="proposal"))
    for field, value in (("actor", "other"), ("reason", "other"), ("expected_revision", 2)):
        changed = MembershipMutation(**{**base, field: value})
        assert changed.fingerprint != mutation.fingerprint
