import os
import pytest

pytestmark=pytest.mark.skipif(os.getenv("RUN_TRINO_INTEGRATION_TESTS")!="1", reason="opt-in disposable Trino 483 test")

def test_live_contract_is_opt_in():
    """The hosted workflow supplies synthetic memory/tpch configuration and runs safe provider suites."""
    assert os.environ.get("TRINO_HOST")
