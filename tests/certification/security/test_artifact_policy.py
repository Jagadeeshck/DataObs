from pathlib import Path


def test_repository_has_no_retained_sentinel_value():
    evidence = Path("certification/evidence")
    forbidden = (
        "DATAOBS_CERT_SENTINEL_DB_PASSWORD",
        "DATAOBS_CERT_SENTINEL_KAFKA_SECRET",
        "DATAOBS_CERT_SENTINEL_WEBHOOK_TOKEN",
        "DATAOBS_CERT_SENTINEL_API_KEY",
    )
    for path in evidence.rglob("*"):
        if path.is_file():
            text = path.read_text(errors="ignore")
            assert not any(value in text for value in forbidden), path
