"""Real-stack openlineage certification contract inventory.

Execution evidence is produced only by the hosted certification backend; this module
keeps scenario names reviewable without representing fixtures as a provider pass.
"""

import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(
    os.getenv("RUN_CERTIFICATION_TESTS") != "1", reason="requires the bounded certification stack"
)


def test_openlineage_certification_harness_is_present():
    assert (ROOT / "docker-compose.certification.yml").exists()
    assert os.getenv("RUN_CERTIFICATION_TESTS") == "1"
