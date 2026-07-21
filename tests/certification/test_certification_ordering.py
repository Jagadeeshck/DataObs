from pathlib import Path

from scripts.certification.validate_workflow_scopes import validate


def test_certification_jobs_follow_blocking_order():
    assert validate(Path(".github/workflows/ci.yml").read_text()) == []


def test_validator_rejects_kafka_seed_after_assertions():
    workflow = Path(".github/workflows/ci.yml").read_text()
    workflow = workflow.replace("create_topics.sh", "create_topics_after_assertions", 1)
    assert "Kafka setup must precede Kafka tests" in validate(workflow)
