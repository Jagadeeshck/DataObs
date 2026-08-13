import os

import pytest


@pytest.mark.skipif(
    os.environ.get("RUN_RABBITMQ_INTEGRATION_TESTS") != "1",
    reason="set RUN_RABBITMQ_INTEGRATION_TESTS=1 with an externally provisioned HTTPS RabbitMQ 4.3.x fixture",
)
def test_externally_provisioned_rabbitmq_fixture_is_required():
    endpoint = os.environ.get("RABBITMQ_MANAGEMENT_ENDPOINT")
    assert endpoint and endpoint.startswith("https://")
