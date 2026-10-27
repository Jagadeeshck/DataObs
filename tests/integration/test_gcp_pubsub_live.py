"""Opt-in externally provisioned Google Pub/Sub validation boundary."""

import os

import pytest


def test_gcp_pubsub_live_resources_are_explicitly_provisioned():
    if os.getenv("RUN_GCP_PUBSUB_INTEGRATION_TESTS") != "1":
        pytest.skip("requires RUN_GCP_PUBSUB_INTEGRATION_TESTS=1 and externally provisioned resources")
    required = ("GCP_PUBSUB_PROJECT_ID", "GCP_PUBSUB_TOPIC", "GCP_PUBSUB_SUBSCRIPTION")
    missing = [name for name in required if not os.getenv(name)]
    assert not missing, f"missing explicit live fixture variables: {', '.join(missing)}"
    assert os.environ["GCP_PUBSUB_TOPIC"].startswith(f"projects/{os.environ['GCP_PUBSUB_PROJECT_ID']}/topics/")
    assert os.environ["GCP_PUBSUB_SUBSCRIPTION"].startswith(
        f"projects/{os.environ['GCP_PUBSUB_PROJECT_ID']}/subscriptions/"
    )
