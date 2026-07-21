def pytest_configure(config):
    for marker in (
        "migrations",
        "postgres",
        "kafka",
        "openlineage",
        "product_queries",
        "incidents",
        "otel",
        "security",
        "browser",
    ):
        config.addinivalue_line("markers", f"{marker}: certification capability evidence group")
