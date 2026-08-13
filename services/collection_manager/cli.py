"""Production composition entrypoint; credentials are never rendered."""

import argparse
import json
import os
import signal

from integrations.aws import AwsDataPlatformProvider
from integrations.aws.configuration import parse_configuration
from integrations.azure import AzureDataPlatformProvider
from integrations.azure.configuration import parse_configuration as parse_azure_configuration
from integrations.bigquery import BigQueryWarehouseProvider
from integrations.bigquery.configuration import parse_configuration as parse_bigquery_configuration
from integrations.databases.mariadb import MariaDbDatabaseProvider
from integrations.databases.mariadb.configuration import parse_configuration as parse_mariadb_configuration
from integrations.databases.mysql import MySqlDatabaseProvider
from integrations.databases.mysql.configuration import parse_configuration as parse_mysql_configuration
from integrations.databases.postgres import PostgreSqlDatabaseProvider
from integrations.databases.postgres.configuration import parse_configuration as parse_postgres_configuration
from integrations.databases.sqlserver import SqlServerDatabaseProvider
from integrations.databases.sqlserver.configuration import parse_configuration as parse_sqlserver_configuration
from integrations.databricks import DatabricksLakehouseProvider
from integrations.databricks.configuration import parse_configuration as parse_databricks_configuration
from integrations.presto import PrestoSqlEngineProvider
from integrations.presto.configuration import parse_configuration as parse_presto_configuration
from integrations.snowflake import SnowflakeWarehouseProvider
from integrations.snowflake.configuration import parse_configuration as parse_snowflake_configuration
from integrations.trino import TrinoSqlEngineProvider
from integrations.trino.configuration import parse_configuration as parse_trino_configuration
from packages.collectors.sdk import ProviderRegistry


def build_registry():
    registry = ProviderRegistry()
    registry.register(AwsDataPlatformProvider)
    registry.register(SnowflakeWarehouseProvider)
    registry.register(DatabricksLakehouseProvider)
    registry.register(BigQueryWarehouseProvider)
    registry.register(AzureDataPlatformProvider)
    registry.register(TrinoSqlEngineProvider)
    registry.register(PrestoSqlEngineProvider)
    registry.register(PostgreSqlDatabaseProvider)
    registry.register(MySqlDatabaseProvider)
    registry.register(MariaDbDatabaseProvider)
    registry.register(SqlServerDatabaseProvider)
    return registry


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("validate-config", "test-connection", "collect-once", "worker", "status"))
    parser.add_argument("--config")
    args = parser.parse_args(argv)
    if not os.environ.get("ELASTICSEARCH_URL"):
        parser.error("ELASTICSEARCH_URL durable storage is required")
    if args.command == "validate-config":
        import yaml

        if not args.config:
            parser.error("--config is required")
        payload = yaml.safe_load(open(args.config, encoding="utf-8"))
        config_parsers = {
            "aws": parse_configuration,
            "snowflake": parse_snowflake_configuration,
            "databricks": parse_databricks_configuration,
            "bigquery": parse_bigquery_configuration,
            "azure": parse_azure_configuration,
            "trino": parse_trino_configuration,
            "presto": parse_presto_configuration,
            "postgres": parse_postgres_configuration,
            "mysql": parse_mysql_configuration,
            "mariadb": parse_mariadb_configuration,
            "sqlserver": parse_sqlserver_configuration,
        }
        config_parsers[payload.get("provider_type")](payload["provider"])
        print(json.dumps({"valid": True}))
        return 0
    # Runtime commands fail closed until Elasticsearch readiness and the trusted tenant/environment are present.
    if not os.environ.get("DATAOBS_TENANT_ID") or not os.environ.get("DATAOBS_ENVIRONMENT"):
        parser.error("trusted tenant and environment are required")
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    print(json.dumps({"ready": False, "reason": "runtime composition requires migrated Elasticsearch"}))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
