import os

import pytest


@pytest.mark.skipif(
    os.getenv("RUN_AZURE_INTEGRATION_TESTS") != "1",
    reason="requires RUN_AZURE_INTEGRATION_TESTS=1 and approved synthetic Azure resources",
)
def test_live_azure_read_only_contract():
    pytest.skip("approved synthetic Azure environment was not supplied; skip is not certification")
