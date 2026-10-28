"""The live-service opt-in must never skip similarly named provider unit suites."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace


def test_live_service_optin_does_not_skip_provider_unit_tests(monkeypatch):
    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location("integration_optin", root / "tests/integration/conftest.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.delenv("RUN_INTEGRATION_TESTS", raising=False)
    live_markers, unit_markers = [], []
    items = [
        SimpleNamespace(path=root / "tests/integration/test_service.py", add_marker=live_markers.append),
        SimpleNamespace(path=root / "tests/integrations/test_provider.py", add_marker=unit_markers.append),
    ]
    module.pytest_collection_modifyitems(None, items)
    assert len(live_markers) == 1
    assert not unit_markers
