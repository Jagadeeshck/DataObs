from src.core.enterprise_blueprint import enterprise_backlog


def test_enterprise_backlog_prioritizes_high_value_low_effort_items():
    backlog = enterprise_backlog([])

    assert backlog[0]["key"] == "data_product_slos"
    assert backlog[0]["priority_score"] == 2.5


def test_enterprise_backlog_excludes_implemented_capabilities():
    backlog = enterprise_backlog(["data_product_slos", "monitor_bootstrap"])

    keys = [item["key"] for item in backlog]
    assert "data_product_slos" not in keys
    assert "monitor_bootstrap" not in keys
