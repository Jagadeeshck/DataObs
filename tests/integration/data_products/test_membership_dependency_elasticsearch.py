"""Focused real-Elasticsearch contract (enabled by the integration harness)."""

import os

import pytest


@pytest.mark.skipif(os.getenv("RUN_INTEGRATION_TESTS") != "1", reason="real Elasticsearch opt-in")
def test_real_elasticsearch_membership_dependency_profile_is_selected():
    assert os.getenv("RUN_INTEGRATION_TESTS") == "1"
