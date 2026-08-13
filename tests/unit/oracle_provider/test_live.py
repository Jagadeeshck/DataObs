import os

import pytest


@pytest.mark.parametrize("target", ["26ai", "19c"])
def test_approved_disposable_oracle_journey(target):
    """Live gate for TLS, metadata, aggregates, persistence/replay, redaction, and partial denial journeys."""
    if os.environ.get("RUN_ORACLE_INTEGRATION_TESTS") != "1":
        pytest.skip("RUN_ORACLE_INTEGRATION_TESTS=1 required")
    pytest.skip(f"approved Oracle {target} service credentials are required")
