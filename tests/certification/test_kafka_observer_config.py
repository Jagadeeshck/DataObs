from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from integrations.kafka.config import KafkaObserverConfig
from services.kafka_observer.cli import _load


def test_certification_config_matches_runtime_model():
    config = KafkaObserverConfig.model_validate(
        yaml.safe_load(Path("certification/config/kafka-observer.yaml").read_text())
    )
    assert config.bootstrap_servers == ["kafka-1:9092", "kafka-2:9092", "kafka-3:9092"]
    assert config.security.protocol == "PLAINTEXT"


def test_cli_loads_certification_config():
    assert _load("certification/config/kafka-observer.yaml").integration_id == "kafka-certification"


def test_old_unsupported_config_is_rejected():
    with pytest.raises(ValidationError):
        KafkaObserverConfig.model_validate(
            {"tenant": "tenant-alpha", "source_id": "old", "bootstrap_servers": "kafka:9092"}
        )
