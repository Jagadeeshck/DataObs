import os, pytest

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_PRESTO_INTEGRATION_TESTS") != "1", reason="set RUN_PRESTO_INTEGRATION_TESTS=1"
)


def test_live_environment_contract():
    assert os.environ.get("PRESTO_HOST")
