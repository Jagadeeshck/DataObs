import os
import pytest


@pytest.mark.skipif(os.getenv("RUN_SNOWFLAKE_INTEGRATION_TESTS") != "1", reason="live Snowflake tests require explicit opt-in and approved sandbox secrets")
def test_live_snowflake_requires_approved_harness():
    required = {"DATAOBS_SNOWFLAKE_ACCOUNT", "DATAOBS_SNOWFLAKE_USER", "DATAOBS_SNOWFLAKE_PRIVATE_KEY"}
    if not required <= set(os.environ):
        pytest.skip("approved sandbox credential references unavailable; this is not validation")
    pytest.skip("hosted harness is intentionally pending independent approval; no certification claim")
